from .table import Table


class DatabaseManager:
    """Manages multiple Table structures within the lightweight DBMS."""

    def __init__(self):
        self.tables = {}

    def create_table(self, table_name, order=4):
        if table_name in self.tables:
            print(f"Error: Table '{table_name}' already exists.")
            return False
        self.tables[table_name] = Table(table_name, order=order)
        print(f"Success: Table '{table_name}' created.")
        return True

    def get_table(self, table_name):
        if table_name not in self.tables:
            print(f"Error: Table '{table_name}' does not exist.")
            return None
        return self.tables[table_name]

    def drop_table(self, table_name):
        if table_name in self.tables:
            del self.tables[table_name]
            print(f"Success: Table '{table_name}' dropped.")
            return True
        print(f"Error: Table '{table_name}' does not exist.")
        return False

    def list_tables(self):
        return list(self.tables.keys())

    def __repr__(self):
        return f"<DatabaseManager tables={self.list_tables()}>"