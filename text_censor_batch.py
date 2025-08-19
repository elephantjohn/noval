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
                        if "words" in hit:
                            violation_info.append(f"  命中词汇: {hit['words']}")
            
            detail = f"结论: {conclusion}"
            if violation_info:
                detail += f"\n详细信息:\n" + "\n".join(violation_info)
            
            return False, detail
        
        return True, f"内容合规 - {conclusion}"
        
    except Exception as e:
        return False, f"结果解析失败: {e}"


def batch_censor_directory(
    directory: Path, 
    censor_client: BaiduTextCensor,
    file_extensions: List[str] = ['.md', '.txt']
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
            
            # 调用审核API
            print(f"  🔍 正在调用审核接口...")
            censor_result = censor_client.censor_text(content)
            
            # 分析结果
            is_compliant, detail = analyze_censor_result(censor_result)
            
            if is_compliant:
                print(f"  ✅ {detail}")
                results[str(file_path)] = {
                    "status": "compliant",
                    "detail": detail,
                    "raw_result": censor_result
                }
            else:
                print(f"  ❌ 审核不通过:")
                for line in detail.split('\n'):
                    print(f"     {line}")
                results[str(file_path)] = {
                    "status": "non_compliant",
                    "detail": detail,
                    "raw_result": censor_result
                }
            
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
                print()


def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python text_censor_batch.py <目录路径>")
        print("示例: python text_censor_batch.py ./chapters")
        sys.exit(1)
    
    target_dir = Path(sys.argv[1])
    
    print("🔍 百度AI文本审核批量检测工具")
    print("=" * 60)
    
    # 加载环境变量
    env_file = Path('.env')
    env_vars = load_env_file(env_file)
    
    api_key = env_vars.get('TEXT_API_KEY') or os.getenv('TEXT_API_KEY')
    secret_key = env_vars.get('TEXT_SECRET_KEY') or os.getenv('TEXT_SECRET_KEY')
    
    if not api_key or not secret_key:
        print("❌ 错误: 未找到 TEXT_API_KEY 或 TEXT_SECRET_KEY")
        print("请在 .env 文件中配置:")
        print("TEXT_API_KEY=your_api_key_here")
        print("TEXT_SECRET_KEY=your_secret_key_here")
        sys.exit(1)
    
    print(f"📂 目标目录: {target_dir.absolute()}")
    print(f"🔑 API密钥: {api_key[:8]}...{api_key[-4:]}")
    print()
    
    try:
        # 初始化审核客户端
        censor_client = BaiduTextCensor(api_key, secret_key)
        
        # 执行批量审核
        results = batch_censor_directory(target_dir, censor_client)
        
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
