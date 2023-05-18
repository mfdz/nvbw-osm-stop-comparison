import logging
import sqlite3
import re

logger = logging.getLogger('osm_stop_matcher.util')

def drop_table_if_exists(db, table):
	try:
		db.execute("DROP TABLE {}".format(table))
	except:
		logger.info('Could not delete table {}'.format(table))
		pass

def create_sequence(db, name):
	try:
		db.execute("CREATE TABLE {} (value int)".format(name))
		db.execute("INSERT INTO {} (value) VALUES(0)".format(name))
	except sqlite3.OperationalError:
		logger.info('Could not create sequence %s', name)

def nextval(db, name):
	try:
		db.execute("UPDATE {} SET value=value+1".format(name))
		cur = db.cursor()
		return cur.execute("select value from {}".format(name)).fetchone()[0]
	except sqlite3.OperationalError:
		logger.info('Could not create sequence %s', name)

def execute_and_ignore_error_if_exists(db, create_statement):
	try:
		db.execute(create_statement)
	except sqlite3.OperationalError:
		logger.info('Could not create table via %s', create_statement)
		pass

def backup_table_if_exists(db, table, backup_table):
	try:
		drop_table_if_exists(db, backup_table)
		db.execute("""CREATE TABLE {} AS
			SELECT * FROM {}""".format(backup_table, table))
	except:
		logger.info('Could not backup table %s'.format(table))
		pass

def xstr(str):
	return None if '' == str else str

def get_parent_station(ifopt_id):
	return re.sub(r'^([^:_]+:[^:_]+:[^:_]+)(_[^:]+)?(:.+)?$', r'\1', ifopt_id)