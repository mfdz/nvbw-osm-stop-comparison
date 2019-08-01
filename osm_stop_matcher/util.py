def drop_table_if_exists(db, table):
	try:
		db.execute("DROP TABLE {}".format(table))
	except:
		print('Could not delete table {}'.format(table))
		pass

def xstr(str):
	return None if '' == str else str
