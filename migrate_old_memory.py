#!/usr/bin/env python3
"""
迁移原有MEMORY.md文件到新的记忆系统
"""
import re
from pathlib import Path
from datetime import datetime
from db_wrapper import MemoryDBWrapper, MemoryOperations
from memory_search import MemorySearch

def migrate_old_memory():
    """迁移旧的MEMORY.md文件到新数据库"""
    old_memory_path = Path("/home/andy/.openclaw/workspace/MEMORY.md")
    
    if not old_memory_path.exists():
        print("未找到旧的MEMORY.md文件，跳过迁移")
        return
    
    print(f"开始迁移旧记忆文件: {old_memory_path}")
    
    with open(old_memory_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 按章节分割
    sections = re.split(r'^#{1,3}\s+', content, flags=re.MULTILINE)
    section_titles = re.findall(r'^#{1,3}\s+(.+)$', content, flags=re.MULTILINE)
    
    with MemoryDBWrapper() as db:
        mem_ops = MemoryOperations(db)
        search = MemorySearch(db)
        
        migrated_count = 0
        
        # 处理序言部分（第一个section是标题前的内容）
        if sections and sections[0].strip():
            preamble = sections[0].strip()
            if len(preamble) > 0:
                l0_summary = preamble[:100].replace('\n', ' ') + "..." if len(preamble) > 100 else preamble
                l1_overview = preamble[:500]
                l2_full_text = preamble
                
                mem_id, _ = search.deduplicated_write(
                    l0_summary=l0_summary,
                    l1_overview=l1_overview,
                    l2_full_text=l2_full_text,
                    memory_type="rule",
                    score=8.0,
                    tier="Core_Soul",
                    is_user_memory=False
                )
                migrated_count += 1
                print(f"✓ 迁移序言部分，ID: {mem_id}")
        
        # 处理各个章节
        for title, content in zip(section_titles, sections[1:]):
            content = content.strip()
            if not content:
                continue
            
            l0_summary = f"{title}: {content[:80].replace('\n', ' ')}..."
            l1_overview = f"# {title}\n\n{content[:450]}"
            l2_full_text = f"# {title}\n\n{content}"
            
            # 识别记忆类型和重要性
            score = 6.0
            memory_type = "fact"
            tier = "LTM"
            is_user_memory = False
            
            if any(keyword in title.lower() for keyword in ['规则', '核心', '必须', '禁止', '安全', '约束']):
                score = 9.0
                memory_type = "rule"
                tier = "Core_Soul"
            elif any(keyword in title.lower() for keyword in ['技能', '工具', '使用方法', '指南']):
                score = 7.5
                memory_type = "skill"
                tier = "LTM"
            elif any(keyword in title.lower() for keyword in ['用户', '偏好', '个人']):
                score = 8.0
                memory_type = "preference"
                tier = "LTM"
                is_user_memory = True
            else:
                # 代理记忆不支持fact类型，默认为state类型
                if not is_user_memory:
                    memory_type = "state"
            
            mem_id, _ = search.deduplicated_write(
                l0_summary=l0_summary,
                l1_overview=l1_overview,
                l2_full_text=l2_full_text,
                memory_type=memory_type,
                score=score,
                tier=tier,
                is_user_memory=memory_type == "preference"
            )
            migrated_count += 1
            print(f"✓ 迁移章节: {title}, ID: {mem_id}")
    
    # 备份旧文件
    backup_path = old_memory_path.with_suffix('.md.bak')
    old_memory_path.rename(backup_path)
    print(f"\n✅ 迁移完成，共迁移 {migrated_count} 条记忆")
    print(f"旧文件已备份为: {backup_path}")

if __name__ == "__main__":
    migrate_old_memory()
