def drop_table_if_exists(db, table):
	try:
		db.execute("DROP TABLE {}".format(table))
	except:
		print('Could not delete table {}'.format(table))
		pass

def backup_table_if_exists(db, table, backup_table):
	try:
		drop_table_if_exists(db, backup_table)
		db.execute("""CREATE TABLE {} AS
			SELECT * FROM {}""".format(backup_table, table))
	except:
		print('Could not backup table {}'.format(table))
		pass

def xstr(str):
	return None if '' == str else str
