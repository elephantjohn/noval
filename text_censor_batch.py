#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百度AI文本审核批量检测工具
对指定目录下的所有文本文件进行内容审核
"""

import os
import sys
import time
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re

# 可选：用于自动修复不合规内容的对话大模型客户端（复用项目里的ERNIE客户端）
try:
    from novel_runner.client import BaiduErnieClient  # type: ignore
except Exception:  # noqa: BLE001
    BaiduErnieClient = None  # type: ignore


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
        # 如果token未过期则直接返回
        if self._access_token and time.time() < (self._token_expiry - 60):
            return self._access_token
        
        print("[TOKEN] 正在获取访问令牌...")
        
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
            expires_in = data.get("expires_in", 2592000)  # 默认30天
            self._token_expiry = time.time() + expires_in
            
            print(f"[TOKEN] 访问令牌获取成功，有效期: {expires_in}秒")
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


def load_env_file(env_path: Path) -> Dict[str, str]:
    """加载.env文件"""
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
    return env_vars


def read_text_file(file_path: Path) -> str:
    """读取文本文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise Exception(f"读取文件失败: {e}")


def analyze_censor_result(result: Dict) -> Tuple[bool, str]:
    """分析审核结果"""
    try:
        # 检查是否有错误
        if "error_code" in result:
            return False, f"API错误 {result['error_code']}: {result.get('error_msg', '未知错误')}"
        
        # 获取审核结论
        conclusion_type = result.get("conclusionType", 1)
        conclusion = result.get("conclusion", "未知")
        
        # conclusionType: 1-合规，2-不合规，3-疑似，4-审核失败
        is_compliant = conclusion_type == 1
        
        if not is_compliant:
            violation_info = []
            
            # 分析具体违规信息
            data = result.get("data", [])
            for item in data:
                if item.get("type") and item.get("msg"):
                    violation_info.append(f"类型:{item['type']} - {item['msg']}")

                    # 详细的命中信息
                    hits = item.get("hits", [])
                    for hit in hits:
                        words = hit.get("words")
                        if isinstance(words, list):
                            joined = "、".join(str(w) for w in words)
                            violation_info.append(f"  命中词汇: {joined}")
                        elif isinstance(words, str):
                            violation_info.append(f"  命中词汇: {words}")
            
            detail = f"结论: {conclusion}"
            if violation_info:
                detail += f"\n详细信息:\n" + "\n".join(violation_info)
            
            return False, detail
        
        return True, f"内容合规 - {conclusion}"
        
    except Exception as e:
        return False, f"结果解析失败: {e}"


def extract_hit_words(detail: str) -> List[str]:
    """从解析后的详情文本中提取命中词汇列表。"""
    hits: List[str] = []
    for line in detail.split("\n"):
        s = line.strip()
        if s.startswith("命中词汇") or s.startswith("命中词"):
            parts = re.split(r"[:：]", s, maxsplit=1)
            if len(parts) == 2:
                words = re.split(r"[、，,\s]+", parts[1].strip())
                hits.extend([w for w in words if w])
    # 去重保持顺序
    seen = set()
    ordered: List[str] = []
    for w in hits:
        if w not in seen:
            seen.add(w)
            ordered.append(w)
    return ordered


def batch_censor_directory(
    directory: Path, 
    censor_client: BaiduTextCensor,
    file_extensions: List[str] = ['.md', '.txt'],
    auto_repair: bool = False,
    repair_client: Optional["BaiduErnieClient"] = None,
    repair_model: str = "ernie-4.5-turbo-128k",
    inplace: bool = False,
    max_rounds: int = 10,
) -> Dict[str, Dict]:
    """批量审核目录下的文件"""
    
    if not directory.exists() or not directory.is_dir():
        raise Exception(f"目录不存在或不是有效目录: {directory}")
    
    # 获取所有符合条件的文件
    files_to_check = []
    for ext in file_extensions:
        files_to_check.extend(directory.glob(f"*{ext}"))
    
    if not files_to_check:
        print(f"[INFO] 目录 {directory} 下没有找到 {file_extensions} 格式的文件")
        return {}
    
    print(f"[INFO] 找到 {len(files_to_check)} 个文件待审核")
    print(f"[INFO] 支持的文件格式: {', '.join(file_extensions)}")
    print("-" * 60)
    
    results = {}
    
    for i, file_path in enumerate(files_to_check, 1):
        print(f"[{i}/{len(files_to_check)}] 正在审核: {file_path.name}")
        
        try:
            # 读取文件内容
            content = read_text_file(file_path)
            
            if not content.strip():
                print(f"  ⚠️  文件为空，跳过审核")
                results[str(file_path)] = {
                    "status": "skipped",
                    "reason": "文件内容为空"
                }
                continue
            
            print(f"  📄 文件大小: {len(content)} 字符")
            
            # 如果内容过长，可能需要分段审核（百度API有长度限制）
            if len(content) > 10000:
                print(f"  ⚠️  文件内容较长({len(content)}字符)，建议分段审核")
            
            # 审核-修复-复审循环
            round_idx = 0
            fixed_path_str = ""
            current_text = content
            current_detail = ""
            current_raw = None
            while True:
                print(f"  🔍 正在调用审核接口...")
                censor_result = censor_client.censor_text(current_text)
                current_raw = censor_result
                is_compliant, detail = analyze_censor_result(censor_result)
                current_detail = detail
                if is_compliant:
                    print(f"  ✅ {detail}")
                    # 通过则根据inplace决定是否写入（若之前有修复过需要落盘）
                    if round_idx > 0:
                        if inplace:
                            file_path.write_text(current_text, encoding="utf-8")
                            fixed_path_str = str(file_path)
                        else:
                            fixed_file = file_path.with_name(file_path.stem + "_修复" + file_path.suffix)
                            fixed_file.write_text(current_text, encoding="utf-8")
                            fixed_path_str = str(fixed_file)
                    results[str(file_path)] = {
                        "status": "compliant",
                        "detail": detail,
                        "raw_result": current_raw,
                        "fixed_file": fixed_path_str,
                    }
                    break
                # 不合规
                print(f"  ❌ 审核不通过:")
                for line in detail.split('\n'):
                    print(f"     {line}")
                if not auto_repair or repair_client is None or round_idx >= max_rounds:
                    # 无法或不再修复，直接返回不合规
                    results[str(file_path)] = {
                        "status": "non_compliant",
                        "detail": detail,
                        "raw_result": current_raw,
                        "fixed_file": fixed_path_str,
                    }
                    break
                # 执行修复
                print(f"  🛠  触发自动修复: 第{round_idx+1}轮 …")
                try:
                    hits = extract_hit_words(detail)
                    fixed_text = auto_repair_text(
                        repair_client=repair_client,
                        model=repair_model,
                        original_text=current_text,
                        violation_hint=detail,
                        hit_words=hits,
                    )
                    current_text = fixed_text
                    round_idx += 1
                    # 中间轮次先落盘为临时文件，便于排查
                    temp_file = file_path.with_name(f"{file_path.stem}_修复_round{round_idx}{file_path.suffix}")
                    temp_file.write_text(current_text, encoding="utf-8")
                    fixed_path_str = str(temp_file)
                    print(f"  ✅ 修复产生 → {fixed_path_str}，将复审…")
                except Exception as e:
                    print(f"  ❌ 修复失败: {e}")
                    results[str(file_path)] = {
                        "status": "error",
                        "detail": f"修复失败: {e}",
                    }
                    break
            
        except Exception as e:
            error_msg = f"处理失败: {e}"
            print(f"  ❌ {error_msg}")
            results[str(file_path)] = {
                "status": "error",
                "detail": error_msg
            }
        
        # 请求间隔，避免频率限制
        if i < len(files_to_check):
            print(f"  ⏱️  等待2秒后继续...")
            time.sleep(2)
        
        print()
    
    return results


def print_summary(results: Dict[str, Dict]):
    """打印审核结果汇总"""
    print("=" * 60)
    print("📊 审核结果汇总")
    print("=" * 60)
    
    total = len(results)
    compliant = sum(1 for r in results.values() if r["status"] == "compliant")
    non_compliant = sum(1 for r in results.values() if r["status"] == "non_compliant")
    errors = sum(1 for r in results.values() if r["status"] == "error")
    skipped = sum(1 for r in results.values() if r["status"] == "skipped")
    
    print(f"总文件数: {total}")
    print(f"✅ 合规: {compliant}")
    print(f"❌ 不合规: {non_compliant}")
    print(f"⚠️  错误: {errors}")
    print(f"⏭️  跳过: {skipped}")
    
    if non_compliant > 0:
        print("\n🚨 不合规文件详情:")
        print("-" * 40)
        for file_path, result in results.items():
            if result["status"] == "non_compliant":
                print(f"📁 {Path(file_path).name}")
                print(f"   {result['detail']}")
                if result.get("fixed_file"):
                    print(f"   🛠  修复文件: {result['fixed_file']}")
                print()


def censor_single_file(
    file_path: Path,
    censor_client: BaiduTextCensor,
    auto_repair: bool = False,
    repair_client: Optional["BaiduErnieClient"] = None,
    repair_model: str = "ernie-4.5-turbo-128k",
    inplace: bool = False,
    max_rounds: int = 10,
) -> Dict[str, Dict]:
    """审核单个文件（支持可选自动修复）。"""
    if not file_path.exists() or not file_path.is_file():
        raise Exception(f"文件不存在或不可读: {file_path}")

    print(f"[FILE] 审核文件: {file_path.name}")
    content = read_text_file(file_path)
    if not content.strip():
        print("  ⚠️  文件为空，跳过审核")
        return {str(file_path): {"status": "skipped", "reason": "文件内容为空"}}

    print(f"  📄 文件大小: {len(content)} 字符")
    if len(content) > 10000:
        print(f"  ⚠️  文件内容较长({len(content)}字符)，建议分段审核")

    # 审核-修复-复审循环
    current_text = content
    fixed_path_str = ""
    for round_idx in range(max_rounds + 1):
        print("  🔍 正在调用审核接口…")
        censor_result = censor_client.censor_text(current_text)
        is_compliant, detail = analyze_censor_result(censor_result)
        if is_compliant:
            print(f"  ✅ {detail}")
            if round_idx > 0:
                if inplace:
                    file_path.write_text(current_text, encoding="utf-8")
                    fixed_path_str = str(file_path)
                else:
                    fixed_file = file_path.with_name(file_path.stem + "_修复" + file_path.suffix)
                    fixed_file.write_text(current_text, encoding="utf-8")
                    fixed_path_str = str(fixed_file)
            return {str(file_path): {
                "status": "compliant",
                "detail": detail,
                "raw_result": censor_result,
                "fixed_file": fixed_path_str,
            }}

        print("  ❌ 审核不通过:")
        for line in detail.split("\n"):
            print(f"     {line}")
        if not auto_repair or repair_client is None or round_idx >= max_rounds:
            return {str(file_path): {
                "status": "non_compliant",
                "detail": detail,
                "raw_result": censor_result,
                "fixed_file": fixed_path_str,
            }}
        print(f"  🛠  触发自动修复: 第{round_idx+1}轮 …")
        hits = extract_hit_words(detail)
        fixed_text = auto_repair_text(
            repair_client=repair_client,
            model=repair_model,
            original_text=current_text,
            violation_hint=detail,
            hit_words=hits,
        )
        current_text = fixed_text
        temp_file = file_path.with_name(f"{file_path.stem}_修复_round{round_idx+1}{file_path.suffix}")
        temp_file.write_text(current_text, encoding="utf-8")
        fixed_path_str = str(temp_file)
        print(f"  ✅ 修复产生 → {fixed_path_str}，将复审…")


def auto_repair_text(
    repair_client: "BaiduErnieClient",
    model: str,
    original_text: str,
    violation_hint: str,
    hit_words: Optional[List[str]] = None,
) -> str:
    """使用大模型自动重写文本为合规版本。"""
    system_prompt = (
        "你是文本合规编辑。\n"
        "只允许对命中违规词所在的句子做最小幅度改写或同义替换, 其他句子一字不动。\n"
        "保持原有信息量与时间顺序与因果关系不变, 不新增人物与事件, 不扩写。\n"
        "返回完整正文, 其余位置保持与原文完全一致, 不加解释。"
    )
    hit_text = "、".join(hit_words) if hit_words else ""
    user_prompt = (
        "【命中词汇】\n" + hit_text +
        "\n\n【不合规提示】\n" + violation_hint +
        "\n\n【修订要求】\n请将上述命中词在原文中替换为不违规但语义相近的表达, 或对包含它们的整句进行改写以移除该词。\n只改这些句子, 其他部分保持完全不变。\n"+
        "\n【待修订正文】\n" + original_text
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    data = repair_client.chat_completions(
        model=model,
        messages=messages,
        temperature=0.4,
        top_p=0.85,
        max_tokens=6000,
    )
    # 兼容多种返回结构
    if isinstance(data, dict):
        if "result" in data and isinstance(data["result"], str):
            return data["result"]
        if "choices" in data:
            choice = data["choices"][0]
            msg = choice.get("message") or {}
            if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                return msg["content"]
    return str(data)


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python text_censor_batch.py <路径> [--auto-repair] [--inplace] [--repair-model=ernie-4.5-turbo-128k] [--max-rounds=10]")
        print("说明: <路径> 可为目录或单个文件")
        print("示例: python text_censor_batch.py ./chapters --auto-repair --repair-model=ernie-4.5-turbo-128k --max-rounds=10")
        sys.exit(1)

    # 简易参数解析
    target_path = Path(sys.argv[1])
    auto_repair = any(arg == "--auto-repair" for arg in sys.argv[2:])
    inplace = any(arg == "--inplace" for arg in sys.argv[2:])
    repair_model = "ernie-4.5-turbo-128k"
    max_rounds = 10
    for arg in sys.argv[2:]:
        if arg.startswith("--repair-model="):
            repair_model = arg.split("=", 1)[1] or repair_model
        if arg.startswith("--max-rounds="):
            try:
                max_rounds = int(arg.split("=", 1)[1])
            except Exception:
                pass
    
    print("🔍 百度AI文本审核批量检测工具")
    print("=" * 60)
    
    # 加载环境变量
    env_file = Path('.env')
    env_vars = load_env_file(env_file)
    
    api_key = env_vars.get('TEXT_API_KEY') or os.getenv('TEXT_API_KEY')
    secret_key = env_vars.get('TEXT_SECRET_KEY') or os.getenv('TEXT_SECRET_KEY')
    baidu_api_key = env_vars.get('BAIDU_API_KEY') or os.getenv('BAIDU_API_KEY')
    
    if not api_key or not secret_key:
        print("❌ 错误: 未找到 TEXT_API_KEY 或 TEXT_SECRET_KEY")
        print("请在 .env 文件中配置:")
        print("TEXT_API_KEY=your_api_key_here")
        print("TEXT_SECRET_KEY=your_secret_key_here")
        sys.exit(1)
    
    label = "目标目录" if target_path.is_dir() else "目标文件"
    print(f"📂 {label}: {target_path.absolute()}")
    print(f"🔑 文本审核AK: {api_key[:8]}...{api_key[-4:]}")
    if auto_repair:
        if BaiduErnieClient is None:
            print("❌ 自动修复不可用: 未找到对话模型客户端依赖。")
            sys.exit(1)
        if not baidu_api_key:
            print("❌ 自动修复不可用: 未配置 BAIDU_API_KEY。")
            sys.exit(1)
        print(f"🛠  自动修复已开启，模型: {repair_model}")
    print()
    
    try:
        # 初始化审核客户端
        censor_client = BaiduTextCensor(api_key, secret_key)

        repair_client = None
        if auto_repair and BaiduErnieClient is not None and baidu_api_key:
            # 复用项目ERNIE客户端，支持直接用 BAIDU_API_KEY
            repair_client = BaiduErnieClient()
        
        # 执行批量审核
        if target_path.is_file():
            results = censor_single_file(
                target_path,
                censor_client,
                auto_repair=auto_repair,
                repair_client=repair_client,
                repair_model=repair_model,
                inplace=inplace,
                max_rounds=max_rounds,
            )
        else:
            results = batch_censor_directory(
                target_path,
                censor_client,
                auto_repair=auto_repair,
                repair_client=repair_client,
                repair_model=repair_model,
                inplace=inplace,
                max_rounds=max_rounds,
            )
        
        # 打印汇总
        print_summary(results)
        
        # 保存详细结果到JSON文件
        result_file = Path("censor_results.json")
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n📄 详细结果已保存到: {result_file.absolute()}")
        
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
