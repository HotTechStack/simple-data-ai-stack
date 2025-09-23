import duckdb
from openai import OpenAI

class TextToSQLAgent:
    def __init__(self, snapshot_path: str, rag=None, fallback_conn_str=None):
        self.snapshot_path = snapshot_path
        self.rag = rag
        self.fallback_conn_str = fallback_conn_str
        self.client = OpenAI()
    
    def query(self, natural_language_query: str):
        """Convert natural language to SQL and execute"""
        
        try:
            context = ""
            if self.rag:
                context = self.rag.query(f"database schema for: {natural_language_query}")
            
            prompt = f"""Given this database context:
{context}

Convert this question to SQL: {natural_language_query}

Return only the SQL query, no explanation."""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            
            sql = response.choices[0].message.content.strip()
            # Clean up SQL if it has markdown code blocks
            sql = sql.replace("```sql", "").replace("```", "").strip()
            
            conn = duckdb.connect(self.snapshot_path, read_only=True)
            result = conn.execute(sql).fetchdf()
            conn.close()
            
            return {"sql": sql, "result": result, "source": "snapshot"}
            
        except Exception as e:
            if self.fallback_conn_str:
                return self._fallback_query(natural_language_query)
            return {"error": str(e), "source": "error"}
    
    def _fallback_query(self, query):
        return {"error": "Snapshot failed, would query live warehouse", "source": "fallback"}