"""
内容审核管理器 - 集成百度文本审核和内容修正
"""
import time
import json
import requests
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import os


class BaiduTextCensor:
    """百度文本审核客户端"""
    
    TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
    CENSOR_URL = "https://aip.baidubce.com/rest/2.0/solution/v1/text_censor/v2/user_defined"
    
    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0.0
    
    def _get_access_token(self) -> str:
        """获取访问令牌"""
        if self._access_token and time.time() < (self._token_expiry - 60):
            return self._access_token
        
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key,
        }
        
        try:
            response = requests.post(self.TOKEN_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "access_token" not in data:
                raise Exception(f"获取token失败: {data}")
            
            self._access_token = data["access_token"]
            expires_in = data.get("expires_in", 2592000)
            self._token_expiry = time.time() + expires_in
            
            return self._access_token
            
        except Exception as e:
            raise Exception(f"获取访问令牌失败: {e}")
    
    def censor_text(self, text: str) -> Dict:
        """审核文本内容"""
        access_token = self._get_access_token()
        
        params = {"access_token": access_token}
        data = {"text": text}
        
        try:
            response = requests.post(
                self.CENSOR_URL, 
                params=params, 
                data=data, 
                timeout=30
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            raise Exception(f"文本审核请求失败: {e}")


class CensorManager:
    """审核管理器"""
    
    def __init__(self, api_key: str, secret_key: str, ernie_client=None, logs_dir: Path = None):
        """
        初始化审核管理器
        
        Args:
            api_key: 文本审核API Key
            secret_key: 文本审核Secret Key
            ernie_client: 百度文心客户端（用于内容修正）
            logs_dir: 日志目录
        """
        self.censor = BaiduTextCensor(api_key, secret_key)
        self.ernie_client = ernie_client
        self.logs_dir = logs_dir
        if logs_dir:
            logs_dir.mkdir(parents=True, exist_ok=True)
    
    def analyze_censor_result(self, result: Dict) -> Tuple[bool, Dict]:
        """
        分析审核结果
        
        Returns:
            (是否通过, 详细信息字典)
        """
        try:
            if "error_code" in result:
                return False, {
                    "error": f"API错误 {result['error_code']}: {result.get('error_msg', '未知错误')}",
                    "violations": []
                }
            
            conclusion_type = result.get("conclusionType", 1)
            conclusion = result.get("conclusion", "未知")
            
            # conclusionType: 1-合规，2-不合规，3-疑似，4-审核失败
            is_compliant = conclusion_type == 1
            
            violations = []
            if not is_compliant:
                data = result.get("data", [])
                for item in data:
                    if item.get("type") and item.get("msg"):
                        violation = {
                            "type": item["type"],
                            "msg": item["msg"],
                            "hits": []
                        }
                        
                        # 提取命中的具体词汇
                        hits = item.get("hits", [])
                        for hit in hits:
                            if "words" in hit:
                                violation["hits"].append(hit["words"])
                        
                        violations.append(violation)
            
            return is_compliant, {
                "conclusion": conclusion,
                "conclusion_type": conclusion_type,
                "violations": violations,
                "raw_result": result
            }
            
        except Exception as e:
            return False, {
                "error": f"结果解析失败: {e}",
                "violations": []
            }
    
    def censor_chapter(self, chapter_text: str, chapter_num: int) -> Tuple[bool, Dict]:
        """
        审核章节内容
        
        Returns:
            (是否通过, 审核详情)
        """
        print(f"[审核] 第{chapter_num}章: 开始内容审核...", flush=True)
        
        try:
            result = self.censor.censor_text(chapter_text)
            is_compliant, details = self.analyze_censor_result(result)
            
            # 保存审核日志
            if self.logs_dir:
                log_file = self.logs_dir / f"censor_{chapter_num:02d}.json"
                with open(log_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "chapter": chapter_num,
                        "compliant": is_compliant,
                        "details": details,
                        "timestamp": time.time()
                    }, f, ensure_ascii=False, indent=2)
            
            if is_compliant:
                print(f"[审核] 第{chapter_num}章: ✅ 审核通过", flush=True)
            else:
                print(f"[审核] 第{chapter_num}章: ❌ 审核不通过", flush=True)
                if details.get("violations"):
                    for v in details["violations"]:
                        print(f"  - {v['type']}: {v['msg']}", flush=True)
                        if v.get("hits"):
                            print(f"    命中词: {', '.join(v['hits'])}", flush=True)
            
            return is_compliant, details
            
        except Exception as e:
            print(f"[审核] 第{chapter_num}章: 审核失败 - {e}", flush=True)
            return False, {"error": str(e), "violations": []}
    
    def fix_violations(self, chapter_text: str, violations: List[Dict], chapter_num: int) -> str:
        """
        使用ernie-4.5-turbo-128k修正违规内容
        
        Args:
            chapter_text: 原始章节文本
            violations: 违规信息列表
            chapter_num: 章节号
            
        Returns:
            修正后的文本
        """
        if not self.ernie_client:
            print(f"[修正] 第{chapter_num}章: 无法修正，未配置ERNIE客户端", flush=True)
            return chapter_text
        
        print(f"[修正] 第{chapter_num}章: 使用ernie-4.5-turbo-128k修正内容...", flush=True)
        
        # 构建违规信息描述
        violation_desc = []
        for v in violations:
            desc = f"- {v['type']}: {v['msg']}"
            if v.get('hits'):
                desc += f" (涉及词汇: {', '.join(v['hits'])})"
            violation_desc.append(desc)
        
        # 构建修正提示词
        fix_prompt = f"""请根据以下审核反馈，对小说文本进行最小化修改，使其符合内容规范。

审核发现的问题：
{chr(10).join(violation_desc)}

修改要求：
1. 只针对上述具体问题进行修改
2. 保持原文的叙事风格和情节发展
3. 尽量使用委婉、隐喻的表达替代直接描述
4. 不要改变故事的核心剧情和人物关系
5. 不要添加新的情节或删除重要内容
6. 只输出修改后的小说正文，不要输出任何说明

原文：
{chapter_text}
"""
        
        messages = [
            {
                "role": "system",
                "content": "你是一位专业的文本编辑，擅长在保持原意的前提下，将内容修改得更加符合平台规范。"
            },
            {
                "role": "user",
                "content": fix_prompt
            }
        ]
        
        try:
            # 使用ernie-4.5-turbo-128k进行修正
            response = self.ernie_client.chat_completions(
                model="ernie-4.5-turbo-128k",
                messages=messages,
                temperature=0.3,  # 低温度，保持稳定
                top_p=0.8,
                max_tokens=5000
            )
            
            # 提取修正后的文本
            if isinstance(response, dict):
                if "result" in response:
                    fixed_text = response["result"]
                elif "choices" in response and response["choices"]:
                    choice = response["choices"][0]
                    if "message" in choice:
                        fixed_text = choice["message"].get("content", "")
                    else:
                        fixed_text = choice.get("content", "")
                else:
                    fixed_text = str(response)
            else:
                fixed_text = str(response)
            
            # 保存修正日志
            if self.logs_dir:
                fix_log = self.logs_dir / f"fix_{chapter_num:02d}.json"
                with open(fix_log, 'w', encoding='utf-8') as f:
                    json.dump({
                        "chapter": chapter_num,
                        "violations": violations,
                        "original_length": len(chapter_text),
                        "fixed_length": len(fixed_text),
                        "timestamp": time.time()
                    }, f, ensure_ascii=False, indent=2)
            
            print(f"[修正] 第{chapter_num}章: 修正完成", flush=True)
            return fixed_text
            
        except Exception as e:
            print(f"[修正] 第{chapter_num}章: 修正失败 - {e}", flush=True)
            return chapter_text
    
    def censor_and_fix_loop(self, chapter_text: str, chapter_num: int, max_retries: int = 3) -> Tuple[bool, str]:
        """
        审核和修正循环
        
        Args:
            chapter_text: 章节文本
            chapter_num: 章节号
            max_retries: 最大重试次数
            
        Returns:
            (是否最终通过, 最终文本)
        """
        current_text = chapter_text
        
        for attempt in range(max_retries + 1):
            # 审核
            is_compliant, details = self.censor_chapter(current_text, chapter_num)
            
            if is_compliant:
                return True, current_text
            
            # 如果是最后一次尝试，不再修正
            if attempt >= max_retries:
                print(f"[审核] 第{chapter_num}章: 已达最大重试次数({max_retries}次)，审核未通过", flush=True)
                return False, current_text
            
            # 修正违规内容
            violations = details.get("violations", [])
            if not violations:
                print(f"[审核] 第{chapter_num}章: 无具体违规信息，无法修正", flush=True)
                return False, current_text
            
            print(f"[审核] 第{chapter_num}章: 第{attempt + 1}次修正...", flush=True)
            current_text = self.fix_violations(current_text, violations, chapter_num)
            
            # 等待一下避免频率限制
            time.sleep(2)
        
        return False, current_text


def generate_chapter_title(chapter_text: str, chapter_num: int, ernie_client) -> str:
    """
    使用ernie-4.5-turbo-128k生成章节标题
    
    Args:
        chapter_text: 章节内容
        chapter_num: 章节号
        ernie_client: ERNIE客户端
        
    Returns:
        章节标题（不含"第X章"）
    """
    print(f"[命名] 第{chapter_num}章: 使用ernie-4.5-turbo-128k生成章节标题...", flush=True)
    
    prompt = f"""请为以下小说章节生成一个精炼的标题。

要求：
1. 标题要体现本章的核心事件或转折
2. 使用2-4个字的词语
3. 有文学性和吸引力
4. 只输出标题本身，不要加"第X章"，不要加任何标点符号
5. 不要输出任何解释或说明

章节内容：
{chapter_text[:1500]}...
"""
    
    messages = [
        {
            "role": "system",
            "content": "你是一位资深的小说编辑，擅长为章节起标题。"
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
    
    try:
        response = ernie_client.chat_completions(
            model="ernie-4.5-turbo-128k",
            messages=messages,
            temperature=0.5,
            top_p=0.85,
            max_tokens=20
        )
        
        # 提取标题
        if isinstance(response, dict):
            if "result" in response:
                title = response["result"].strip()
            elif "choices" in response and response["choices"]:
                choice = response["choices"][0]
                if "message" in choice:
                    title = choice["message"].get("content", "").strip()
                else:
                    title = choice.get("content", "").strip()
            else:
                title = f"章节{chapter_num}"
        else:
            title = str(response).strip()
        
        # 清理标题（移除可能的标点）
        title = title.strip('。，、；：""''《》【】')
        
        # 确保标题不要太长
        if len(title) > 8:
            title = title[:8]
        
        print(f"[命名] 第{chapter_num}章: 标题生成完成 - {title}", flush=True)
        return title
        
    except Exception as e:
        print(f"[命名] 第{chapter_num}章: 标题生成失败 - {e}", flush=True)
        return f"章节{chapter_num}"