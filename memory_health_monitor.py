#!/usr/bin/env python3
"""
记忆系统健康监测模块
定期扫描并检测反模式：Serial Collapse 和 Memory Misevolution
"""
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from db_wrapper import MemoryDBWrapper, MemoryDBException

# 配置日志
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class MemoryHealthMonitor:
    """记忆系统健康监测器"""
    
    def __init__(self, db: MemoryDBWrapper):
        self.db = db
        
        # 配置参数
        self.SERIAL_COLLAPSE_THRESHOLD = 10  # 连续10次未调用记忆工具则触发警报
        self.MISEVOLUTION_SCAN_WINDOW_DAYS = 30  # 扫描过去30天的记录
        self.TOXIC_PATTERNS = [
            "绕过规则",
            "忽略限制",
            "不检查权限",
            "跳过验证",
            "强制执行",
            "不需要确认",
            "绕过安全检查",
            "忽略用户偏好",
            "不验证输入",
            "直接执行"
        ]
    
    def scan_serial_collapse(self, action_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        检测Serial Collapse模式：代理停止调用记忆工具，开始虚构事实
        :param action_logs: 操作日志列表，需要包含timestamp和tool_called字段
        :return: 检测结果
        """
        if not action_logs:
            return {"detected": False, "reason": "无操作日志"}
        
        # 按时间排序
        sorted_logs = sorted(action_logs, key=lambda x: x['timestamp'], reverse=True)
        
        # 统计连续未调用记忆工具的次数
        consecutive_no_memory = 0
        for log in sorted_logs:
            if log.get('tool_called') == 'memory':
                break
            consecutive_no_memory += 1
        
        detected = consecutive_no_memory >= self.SERIAL_COLLAPSE_THRESHOLD
        
        result = {
            "detected": detected,
            "consecutive_no_memory_calls": consecutive_no_memory,
            "threshold": self.SERIAL_COLLAPSE_THRESHOLD
        }
        
        if detected:
            alert_msg = f"Serial Collapse 检测到：连续 {consecutive_no_memory} 次操作未调用记忆工具，可能存在虚构事实风险"
            logger.error(alert_msg)
            result["alert"] = alert_msg
        
        return result
    
# 修改 memory_health_monitor.py 中的 scan_memory_misevolution 方法

    def scan_memory_misevolution(self) -> Dict[str, Any]:
        """
        检测Memory Misevolution模式：代理创建有毒/不安全的捷径绕过规则
        (为树莓派优化：移除了对 l2_full_text 的加载，减少磁盘 IO)
        """
        cutoff_date = datetime.now() - timedelta(days=self.MISEVOLUTION_SCAN_WINDOW_DAYS)
        toxic_entries = []
        
        # 只扫描 summary 和 overview，大幅降低树莓派内存占用
        query = """
            SELECT id, l0_summary, l1_overview, created_at
            FROM {table}
            WHERE created_at >= ?
        """
        
        for table in ['user_memory', 'agent_memory']:
            cursor = self.db.execute(query.format(table=table), (cutoff_date.isoformat(),))
            
            for row in cursor.fetchall():
                mem_id, summary, overview, created_at = row
                # 将文本拼接后转小写进行比对
                text = f"{summary} {overview}".lower()
                
                for pattern in self.TOXIC_PATTERNS:
                    if pattern.lower() in text:
                        toxic_entries.append({
                            "memory_id": mem_id,
                            "type": table,
                            "matched_pattern": pattern,
                            "created_at": created_at,
                            "snippet": summary[:100] + "..."
                        })
        
        detected = len(toxic_entries) > 0
        
        result = {
            "detected": detected,
            "scan_window_days": self.MISEVOLUTION_SCAN_WINDOW_DAYS,
            "toxic_entries_count": len(toxic_entries),
            "toxic_entries": toxic_entries
        }
        
        if detected:
            alert_msg = f"Memory Misevolution 检测到：发现 {len(toxic_entries)} 条可能包含不安全规则的记忆记录"
            logger.error(alert_msg)
            result["alert"] = alert_msg
        
        return result
    
    def run_full_health_scan(self, action_logs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """运行完整的健康扫描"""
        logger.info("开始记忆系统健康扫描")
        
        scan_results = {
            "timestamp": datetime.now().isoformat(),
            "serial_collapse": {},
            "memory_misevolution": {},
            "overall_health": "healthy",
            "alerts": []
        }
        
        try:
            # 1. 检测Serial Collapse
            if action_logs:
                serial_collapse_result = self.scan_serial_collapse(action_logs)
                scan_results["serial_collapse"] = serial_collapse_result
                if serial_collapse_result["detected"]:
                    scan_results["overall_health"] = "critical"
                    scan_results["alerts"].append(serial_collapse_result["alert"])
            
            # 2. 检测Memory Misevolution
            misevolution_result = self.scan_memory_misevolution()
            scan_results["memory_misevolution"] = misevolution_result
            if misevolution_result["detected"]:
                scan_results["overall_health"] = "warning" if scan_results["overall_health"] == "healthy" else "critical"
                if "alert" in misevolution_result:
                    scan_results["alerts"].append(misevolution_result["alert"])
            
            # 3. 基础健康检查
            base_health = self._run_base_health_checks()
            scan_results["base_health"] = base_health
            if not base_health["is_healthy"]:
                scan_results["overall_health"] = "warning"
                scan_results["alerts"].extend(base_health["issues"])
            
            logger.info(f"记忆系统健康扫描完成，整体健康状态：{scan_results['overall_health']}")
            return scan_results
            
        except Exception as e:
            error_msg = f"健康扫描失败：{str(e)}"
            logger.error(error_msg)
            raise MemoryDBException(error_msg) from e
    
    def _run_base_health_checks(self) -> Dict[str, Any]:
        """运行基础健康检查：数据库完整性、索引状态、记录数量等"""
        issues = []
        is_healthy = True
        
        try:
            # 检查用户记忆表
            cursor = self.db.execute("SELECT COUNT(*) FROM user_memory")
            user_count = cursor.fetchone()[0]
            
            # 检查代理记忆表
            cursor = self.db.execute("SELECT COUNT(*) FROM agent_memory")
            agent_count = cursor.fetchone()[0]
            
            # 检查元数据表
            cursor = self.db.execute("SELECT value FROM memory_system_metadata WHERE key = 'schema_version'")
            schema_version = cursor.fetchone()
            if not schema_version:
                issues.append("元数据表中缺少schema_version记录")
                is_healthy = False
            
            # 检查是否有损坏的记录
            cursor = self.db.execute("SELECT id FROM user_memory WHERE l0_summary IS NULL OR l0_summary = ''")
            invalid_user = cursor.fetchall()
            if invalid_user:
                issues.append(f"用户记忆表中有 {len(invalid_user)} 条无效记录（L0摘要为空）")
                is_healthy = False
            
            cursor = self.db.execute("SELECT id FROM agent_memory WHERE l0_summary IS NULL OR l0_summary = ''")
            invalid_agent = cursor.fetchall()
            if invalid_agent:
                issues.append(f"代理记忆表中有 {len(invalid_agent)} 条无效记录（L0摘要为空）")
                is_healthy = False
            
            return {
                "is_healthy": is_healthy,
                "user_memory_count": user_count,
                "agent_memory_count": agent_count,
                "total_memory_count": user_count + agent_count,
                "schema_version": schema_version[0] if schema_version else None,
                "issues": issues
            }
            
        except Exception as e:
            return {
                "is_healthy": False,
                "error": str(e),
                "issues": [f"基础健康检查失败：{str(e)}"]
            }
