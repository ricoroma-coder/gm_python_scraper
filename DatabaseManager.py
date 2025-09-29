import sqlite3


class DatabaseManager:
    """Classe para gerenciar interações com o banco de dados SQLite"""

    def __init__(self, db_path="products.db"):
        self.db_path = db_path
        self.connection = None
        self._create_database()

    def _create_database(self):
        """Cria o banco de dados e a tabela se não existirem"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_type TEXT NOT NULL,
                name TEXT,
                description TEXT,
                link TEXT,
                images TEXT,
                rating REAL,
                rating_count INTEGER,
                facilities TEXT,
                latitude REAL,
                longitude REAL,
                phone TEXT,
                address TEXT,
                stars INTEGER,
                price TEXT,
                card_href TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def connect(self):
        """Inicia a conexão com o banco de dados"""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row  # Para retornar resultados como dicionário

    def disconnect(self):
        """Encerra a conexão com o banco de dados"""
        if self.connection:
            self.connection.close()
            self.connection = None

    def get(self, sql_statement, params=None):
        """Executa uma query SQL no banco de dados"""
        self.connect()
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(sql_statement, params)
            else:
                cursor.execute(sql_statement)

            results = cursor.fetchall()
            return [dict(row) for row in results]

        except Exception as e:
            print(f"Error executing query: {str(e)}")
            return []
        finally:
            self.disconnect()

    def create(self, data):
        """Insere um novo registro no banco de dados"""
        self.connect()
        try:
            cursor = self.connection.cursor()

            # Monta a query dinamicamente baseado nos campos fornecidos
            fields = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data.values()])

            sql = f"INSERT INTO products ({fields}) VALUES ({placeholders})"
            cursor.execute(sql, list(data.values()))

            self.connection.commit()
            return cursor.lastrowid

        except Exception as e:
            print(f"Error creating record: {str(e)}")
            return None
        finally:
            self.disconnect()

    def update(self, record_id, data):
        """Atualiza um registro existente no banco de dados"""
        self.connect()
        try:
            cursor = self.connection.cursor()

            # Monta a query dinamicamente baseado nos campos fornecidos
            set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
            sql = f"UPDATE products SET {set_clause} WHERE id = ?"

            params = list(data.values()) + [record_id]
            cursor.execute(sql, params)

            self.connection.commit()
            return cursor.rowcount > 0  # Retorna True se alguma linha foi afetada

        except Exception as e:
            print(f"Error updating record: {str(e)}")
            return False
        finally:
            self.disconnect()

    def destroy(self, record_id):
        """Remove um registro do banco de dados"""
        self.connect()
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM products WHERE id = ?", (record_id,))

            self.connection.commit()
            return cursor.rowcount > 0  # Retorna True se alguma linha foi removida

        except Exception as e:
            print(f"Error deleting record: {str(e)}")
            return False
        finally:
            self.disconnect()