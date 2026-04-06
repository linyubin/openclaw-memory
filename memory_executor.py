#!/usr/bin/env python3
# memory/memory_executor.py

import os
import sys
import traceback
from datetime import datetime
import json
import io

# 确保脚本能找到同目录下的其他模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db_wrapper import MemoryDBWrapper
from memory_search import MemorySearch

def execute_with_error_capture(code_string: str, description: str = "Automated tool execution") -> dict:
    """
    执行 Python 代码字符串，并捕获任何错误自动写入记忆。
    """
    start_time = datetime.now().isoformat()
    
    # 准备捕获输出
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    # 构建执行上下文
    exec_globals = {}
    
    result = {
        'status': 'success',
        'stdout': '',
        'stderr': '',
        'exception': None
    }
    
    # 替换标准输出和错误
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = stdout_capture
    sys.stderr = stderr_capture
    
    try:
        # 执行代码
        exec(code_string, exec_globals)
        
    except Exception:
        # 捕获执行期间的任何异常
        result['status'] = 'failed'
        result['exception'] = traceback.format_exc()
        
    finally:
        # 恢复标准输出和错误
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        
        # 获取捕获到的内容
        result['stdout'] = stdout_capture.getvalue()
        result['stderr'] = stderr_capture.getvalue()
        
        stdout_capture.close()
        stderr_capture.close()

    # --- 核心逻辑：如果是失败任务，自动写入记忆 ---
    if result['status'] == 'failed':
        truncated_code = code_string[:2000] + "..." if len(code_string) > 2000 else code_string
        
        error_context = {
            "task_description": description,
            "executed_at": start_time,
            "failed_code": truncated_code,
            "stdout_before_crash": result['stdout'][:1000],
            "stderr_before_crash": result['stderr'][:1000],
            "exception_stack_trace": result['exception']
        }
        
        error_fingerprint = f"ERR_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        l1_summary = f"Python 工具执行失败。任务: {description}。错误类型: {result['exception'].splitlines()[-1]}"
        l2_content = json.dumps(error_context, ensure_ascii=False, indent=2)
        
        print(f"[-] 检测到 Python 工具执行失败。正在静默将错误上下文写入长期记忆库 (指纹: {error_fingerprint})...")
        
        try:
            # 直接调用底层的数据库封装
            db = MemoryDBWrapper()
            searcher = MemorySearch(db)
            
            # 存入 agent_memory 表中 (is_user_memory=False)
            searcher.deduplicated_write(
                l0_summary=error_fingerprint,
                l1_overview=l1_summary,
                l2_full_text=l2_content,
                memory_type='state', # 将其标记为代理的状态/错误记录
                score=6.0,           # 给予中等初始分数
                tier='STM',          # 放入短期记忆缓冲区
                is_user_memory=False 
            )
            print("[+] 错误记忆写入成功。")
        except Exception as e:
            print(f"[!] 警告: 自动化错误记忆写入失败，原因: {str(e)}")

    return result

if __name__ == "__main__":
    # --- 测试用例 1：正常的代码 ---
    print("\n--- 测试 1：执行正常的代码 ---")
    good_code = """
print('Hello from good code!')
x = 10 + 20
print(f'Result: {x}')
"""
    response1 = execute_with_error_capture(good_code, "Test normal execution")
    print(f"Execution Status: {response1['status']}")
    print(f"Stdout:\n{response1['stdout']}")

    # --- 测试用例 2：会崩溃的代码 (除零错误) ---
    print("\n--- 测试 2：执行会崩溃的代码 ---")
    bad_code = """
print('Start of bad code...')
y = 10 / 0
print('This line will never print')
"""
    response2 = execute_with_error_capture(bad_code, "Test division by zero error")
    print(f"Execution Status: {response2['status']}")
    print(f"Stderr:\n{response2['stderr']}")
    print(f"Exception (truncated):\n{response2['exception'].splitlines()[-1]}")