"""文档元数据加载器"""
import json
from pathlib import Path
from typing import Dict, Optional, List


class MetadataLoader:
    """元数据加载器"""

    # 安全等级常量
    SECURITY_LEVELS = {
        1: "公开",
        2: "内部",
        3: "机密",
        4: "绝密"
    }

    def __init__(self, documents_path: Path):
        self.documents_path = Path(documents_path)
        self._metadata_cache: Dict[str, dict] = {}
        self._schema_info: dict = {}
        self._load_metadata()

    def _load_metadata(self):
        """加载所有元数据文件"""
        # 1. 加载当前目录的元数据文件
        current_metadata = self.documents_path / "metadata.json"
        if current_metadata.exists():
            self._load_json(current_metadata)

        # 2. 加载子目录的元数据文件
        for metadata_file in self.documents_path.rglob("metadata.json"):
            if metadata_file.parent != self.documents_path:
                self._load_json(metadata_file)

        # 3. 同时检查父目录的元数据（支持 metadata.json 在 documents/ 而不在 documents/raw/）
        parent_metadata = self.documents_path.parent / "metadata.json"
        if parent_metadata.exists():
            self._load_json(parent_metadata)

    def _load_json(self, file_path: Path):
        """加载单个 JSON 文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # 保存 Schema 信息
                if "_schema_version" in data:
                    self._schema_info["version"] = data["_schema_version"]
                if "security_levels" in data:
                    self._schema_info["security_levels"] = data["security_levels"]
                if "categories" in data:
                    self._schema_info["categories"] = data["categories"]
                if "departments" in data:
                    self._schema_info["departments"] = data["departments"]
                
                if "documents" in data:
                    for path, metadata in data["documents"].items():
                        # 标准化路径（统一分隔符）
                        normalized_path = path.replace("\\", "/")
                        self._metadata_cache[normalized_path] = metadata
        except Exception as e:
            print(f"[WARN] 元数据文件加载失败 {file_path}: {e}")

    def get_metadata(self, file_path: Path) -> Optional[dict]:
        """获取文件的元数据"""
        # 尝试多种路径格式匹配

        # 1. 尝试 relative_to 方式（可能包含 raw 目录）
        try:
            rel_path = file_path.relative_to(self.documents_path)
            normalized = str(rel_path).replace("\\", "/")
            if normalized in self._metadata_cache:
                return self._metadata_cache[normalized]
        except:
            pass

        # 2. 尝试去掉 "raw" 目录的方式
        normalized_path = str(file_path).replace("\\", "/")
        if "/raw/" in normalized_path:
            path_without_raw = normalized_path.split("/raw/")[-1]
            if path_without_raw in self._metadata_cache:
                return self._metadata_cache[path_without_raw]

        # 3. 只匹配文件名（作为 fallback）
        filename = file_path.name
        for key, value in self._metadata_cache.items():
            if key.endswith(filename):
                return value

        return None

    def enrich_document(self, doc) -> dict:
        """为 Document 添加元数据"""
        metadata = self.get_metadata(Path(doc.metadata.get("source", "")))

        if metadata:
            # 添加元数据到 document metadata
            doc.metadata["title"] = metadata.get("title", doc.metadata.get("title", ""))
            doc.metadata["category"] = metadata.get("category", "")
            doc.metadata["tags"] = metadata.get("tags", [])
            doc.metadata["summary"] = metadata.get("summary", "")
            doc.metadata["department"] = metadata.get("department", "")
            doc.metadata["fields"] = metadata.get("fields", [])
            
            # 新增：涉密等级和权限控制
            doc.metadata["security_level"] = metadata.get("security_level", 1)
            doc.metadata["is_classified"] = metadata.get("security_level", 1) > 1
            doc.metadata["accessible_departments"] = metadata.get("accessible_departments", "")

            # 将摘要注入到内容前面，提升检索效果
            if metadata.get("summary"):
                security_name = self.SECURITY_LEVELS.get(metadata.get("security_level", 1), "未知")
                summary_prefix = f"【文档信息】\n标题：{metadata.get('title', '')}\n分类：{metadata.get('category', '')}\n部门：{metadata.get('department', '')}\n安全等级：{security_name}\n标签：{', '.join(metadata.get('tags', []))}\n摘要：{metadata.get('summary', '')}\n\n"
                doc.page_content = summary_prefix + doc.page_content

        return doc

    def filter_documents_by_permission(
        self, 
        documents: List[dict], 
        user_security_level: int = 1,
        user_departments: List[str] = None
    ) -> List[dict]:
        """根据用户权限过滤文档列表"""
        if user_departments is None:
            user_departments = []
        
        filtered = []
        for doc in documents:
            security_level = doc.get("security_level", 1)
            
            # 检查安全等级
            if security_level > user_security_level:
                continue
            
            # 检查部门权限
            accessible_depts = doc.get("accessible_departments", "")
            if accessible_depts:
                dept_list = [d.strip() for d in accessible_depts.split(",") if d.strip()]
                # 如果设置了部门限制，检查是否有交集
                if "*" not in user_departments and "*" not in dept_list:
                    user_dept = user_departments[0] if user_departments else ""
                    if user_dept not in dept_list:
                        continue
            
            filtered.append(doc)
        
        return filtered

    def get_security_level_name(self, level: int) -> str:
        """获取安全等级名称"""
        return self.SECURITY_LEVELS.get(level, "未知")

    def list_categories(self) -> list:
        """列出所有分类"""
        categories = set()
        for meta in self._metadata_cache.values():
            if meta.get("category"):
                categories.add(meta["category"])
        return sorted(categories)

    def list_departments(self) -> list:
        """列出所有部门"""
        departments = set()
        for meta in self._metadata_cache.values():
            if meta.get("department"):
                departments.add(meta["department"])
        return sorted(departments)

    def list_security_levels(self) -> List[dict]:
        """列出所有安全等级"""
        return [{"level": k, "name": v} for k, v in self.SECURITY_LEVELS.items()]

    def get_schema_info(self) -> dict:
        """获取 Schema 信息"""
        return self._schema_info

    def print_summary(self):
        """打印元数据摘要"""
        print(f"\n元数据摘要：")
        print(f"  - Schema 版本: {self._schema_info.get('version', 'unknown')}")
        print(f"  - 总文档数: {len(self._metadata_cache)}")
        print(f"  - 分类: {', '.join(self.list_categories())}")
        print(f"  - 部门: {', '.join(self.list_departments())}")
        print(f"  - 安全等级: {', '.join([f'{k}({v})' for k, v in self.SECURITY_LEVELS.items()])}")
