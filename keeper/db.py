import sqlite3

from flask import g, current_app
from flask.cli import with_appcontext

import click

from keeper.manager import KeeperException

def get_db():
  if 'db' not in g:
    g.db = sqlite3.connect(
      current_app.config['DATABASE'],
      detect_types=sqlite3.PARSE_DECLTYPES
    )
    g.db.row_factory = sqlite3.Row
  return g.db

def close_db(e=None):
  db = g.pop('db', None)
  if db is not None:
    db.close()

def init_db():
  db = get_db()
  with current_app.open_resource('schema.sql') as f:
    db.executescript(f.read().decode('utf8'))

@click.command('init-db')
@with_appcontext
def init_db_command():
  init_db()
  click.echo('Initialized the database.')

def init_app(app):
  app.teardown_appcontext(close_db)
  app.cli.add_command(init_db_command)

def get_user_info(username):
  return get_db().execute(
    '''select user_id, token from user u where username = ?''', (username,)
  ).fetchone()

def get_user_token_by_project(project_id):
  return get_db().execute(
    '''select u.token as token from user u left join user_project up on u.user_id = up.user_id where up.project_id = ?''', (project_id,)
  ).fetchone()

def get_user_by_id(user_id):
  return get_db().execute(
    '''select user_id, username, token from user where user_id = ?''', (user_id,)
  ).fetchone()

def get_vm(name):
  vm = get_db().execute(
    '''select v.vm_id , v.vm_name, v.target, v.keeper_url, vs.snapshot_name from vm v
      left join vm_snapshot vs on v.vm_id = vs.vm_id
    where v.vm_name = ?''', (name,)
  ).fetchone()
  return vm

def get_project_runner(vm_name):
  return get_db().execute(
    '''select v.vm_id, v.vm_name, v.target, v.keeper_url, r.runner_id, vs.snapshot_name, u.token
        from project p
          left join project_runner pr on p.project_id = pr.project_id
          left join user_project up on up.project_id = pr.project_id
          left join user u on u.user_id = up.user_id
          left join runner r on pr.runner_id = r.runner_id
          left join vm v on v.vm_id = pr.vm_id
          left join vm_snapshot vs on vs.vm_id = v.vm_id
       where v.vm_name = ?''', (vm_name,)
  ).fetchone()

def get_project_by_user_id(project_name, user_id):
  return get_db().execute(
    '''select p.project_id, p.project_name, u.username
         from project p
           left join user_project up on up.project_id = p.project_id
           left join user u on up.user_id = u.user_id
         where p.project_name = ? and u.user_id = ?''', (project_name, user_id)
  ).fetchone()

def get_project_runner_by_name(runner_name):
  return get_db().execute(
    '''select p.project_id, r.runner_id, v.vm_id, vs.snapshot_name from runner r
          left join project_runner pr on pr.runner_id = r.runner_id
          left join project p on p.project_id = pr.project_id
          left join vm v on v.vm_id = pr.vm_id
          left join vm_snapshot vs on vs.vm_id = v.vm_id
        where r.runner_name = ?
    ''', (runner_name,)
  ).fetchall()

def get_runner_token(username, project_name):
  return get_db().execute(
    '''select p.project_id, p.project_name, p.runner_token from project p
        left join user_project up on up.project_id = p.project_id
        left join user u on u.user_id = up.user_id
        where u.username = ? and p.project_name = ?
    ''', (username, project_name)
  ).fetchone()

def get_vm_snapshot(vm_name):
  return get_db().execute(
    '''select v.vm_id, v.vm_name, v.target, v.keeper_url, vs.snapshot_name from vm v 
        left join vm_snapshot vs on v.vm_id = vs.vm_id 
       where v.vm_name = ?''', (vm_name,)
  ).fetchone()

def check_vm_snapshot(vm_name, snapshot_name, app):
  return get_db().execute(
    '''select v.vm_id from vm v 
        left join vm_snapshot vs on v.vm_id = vs.vm_id
        where v.vm_name = ? and vs.snapshot_name = ?
    ''', (vm_name, snapshot_name)
  ).fetchone()

def check_user(username, app):
  return get_db().execute(
    '''select count() as cnt from user u
        where u.username = ?
    ''', (username,)
  ).fetchone()

def check_user_project(username, project_name, app):
  return get_db().execute(
      '''select count() as cnt from user u
          left join user_project up on u.user_id = up.user_id
          left join project p on p.project_id = up.project_id
          where u.username = ? and p.project_name = ?
      ''', (username, project_name)
    ).fetchone()

def check_project_runner(project_name, vm_name, runner_id, snapshot_name, app):
  return get_db().execute(
    '''select count() as cnt from runner r
        left join project_runner pr on r.runner_id = pr.runner_id
        left join project p on p.project_id = pr.project_id
        left join vm v on v.vm_id = pr.vm_id
        left join vm_snapshot vs on vs.vm_id = pr.vm_id
        where p.project_id = ? and r.runner_id = ? and v.vm_name = ? and vs.snapshot_name = ?
    ''', (project_name, runner_id, vm_name, snapshot_name)
  ).fetchone()

def check_issue_exists(user_id, issue_hash):
  return get_db().execute(
    '''select count() as cnt from user_issue ui
         where ui.user_id = ? and ui.issue_hash = ?
    ''', (user_id, issue_hash)
  ).fetchone()

def get_note_template(name):
  return get_db().execute(
    '''select template_name, template_content from note_template
         where template_name = ? ''', (name,)
  ).fetchone()

def get_available_ip_by_project(project_id):
  return get_db().execute(
    '''select min(ip.id) id, min(ip.ip_address) ip_address, min(ip.project_id) project_id
          from ip_provision ip 
         left join ip_runner ir on ir.ip_provision_id = ip.id
         where  ip.is_allocated = 0
            and ip.project_id = ?''', (project_id,)
  ).fetchone()

def get_ip_provision_by_pipeline(pipeline_id):
  return get_db().execute(
    '''select ir.ip_provision_id, ir.pipeline_id, ip.ip_address, ip.project_id from ip_runner ir
          left join ip_provision ip on ip.id = ir.ip_provision_id
          where ir.pipeline_id = ?
    ''',(pipeline_id,)
  ).fetchone()

def proxied_execute(app, sql, *data):
  if "CONN" in app.config and app.config["CONN"]:
    c = app.config["CONN"]
    c.execute(sql, *data)
  else:
    c = get_db()
    try:
      c.execute(sql, *data)
      c.commit()
    except Exception as e:
      app.logger.error(e)
      c.rollback()
      raise KeeperException(500, e)
  
def insert_vm(vm, app):
  proxied_execute(app, 'insert into vm (vm_id, vm_name, target, keeper_url) values (?, ?, ?, ?)', (vm.vm_id, vm.vm_name, vm.target, vm.keeper_url))

def insert_snapshot(snapshot, app):
  proxied_execute(app, 'insert into vm_snapshot (vm_id, snapshot_name) values (?, ?)', (snapshot.vm_id, snapshot.snapshot_name))

def insert_user(user, app):
  proxied_execute(app, 'insert into user (user_id, username, token) values (?, ?, ?)', (user.user_id, user.username, user.token))

def insert_project(project, app):
  proxied_execute(app, 'insert into project (project_id, project_name) values (?, ?)', (project.project_id, project.project_name))

def insert_user_project(user, project, app):
  proxied_execute(app, 'insert into user_project (project_id, user_id) values (?, ?)', (project.project_id, user.user_id))

def insert_runner(runner, app):
  proxied_execute(app, 'replace into runner (runner_id, runner_name) values (?, ?)', (runner.runner_id, runner.runner_name))

def insert_project_runner(project, vm, runner, app):
  proxied_execute(app, 'replace into project_runner (project_id, vm_id, runner_id) values (?, ?, ?)', (project.project_id, vm.vm_id, runner.runner_id))

def delete_project_runner(project_id, runner_id, app):
  proxied_execute(app, 'delete from project_runner where project_id = ? and runner_id = ?', (project_id, runner_id))

def delete_runner(runner_id, app):
  proxied_execute(app, 'delete from runner where runner_id = ?', (runner_id,))

def delete_vm(vm_id, app):
  proxied_execute(app, 'delete from vm where vm_id = ?', (vm_id,))

def delete_snapshot(snapshot_name, app):
  proxied_execute(app, 'delete from vm_snapshot where snapshot_name = ?', (snapshot_name,))

def insert_issue_hash_with_user(user_id, issue_hash, app):
  proxied_execute(app, 'insert into user_issue (user_id, issue_hash) values (?, ?)', (user_id, issue_hash))

def insert_note_template(name, template, app):
  proxied_execute(app, 'replace into note_template (template_name, template_content) values (?, ?)', (name, template))

def update_runner_token(runner_token, project_id, app):
  proxied_execute(app, 'update project set runner_token = ? where project_id = ?', (runner_token, project_id))

def insert_ip_provision(ip_address, project_id, app):
  proxied_execute(app, 'replace into ip_provision (ip_address, project_id) values (?, ?)', (ip_address, project_id))

def delete_ip_provision(project_id, app):
  proxied_execute(app, 'delete from ip_provision where project_id = ?', (project_id,))

def insert_ip_runner(ip_provision_id, pipeline_id, app):
  proxied_execute(app, 'insert into ip_runner (ip_provision_id, pipeline_id) values (?, ?)', (ip_provision_id, pipeline_id))

def update_ip_runner(ip_provision_id, runner_id, app):
  proxied_execute(app, 'update ip_runner set runner_id = ? where ip_provision_id = ?', (runner_id, ip_provision_id))

def remove_ip_runner(ip_provision_id, app):
  proxied_execute(app, 'delete from ip_runner where ip_provision_id = ?', (ip_provision_id,))

def remove_ip_runner_by_project_id(project_id, app):
  proxied_execute(app, '''
    delete from ip_runner where ip_provision_id in (
      select ip_provision_id from ip_provision
        where project_id = ?)
  ''', (project_id,))

def update_ip_provision_by_id(ip_provision_id, is_allocated, app):
  proxied_execute(app, 'update ip_provision set is_allocated = ? where id = ?', (is_allocated, ip_provision_id))

def update_ip_provision_by_project_id(project_id, is_allocated, app):
  proxied_execute(app, 'update ip_provision set is_allocated = ? where project_id = ?', (is_allocated, project_id))

class DBT:
  conn = None
  @classmethod
  def __get_conn(cls, app):
    cls.conn = get_db()
    app.config["CONN"] = cls.conn

  @classmethod
  def __commit(cls):
    cls.conn.commit()

  @classmethod
  def __rollback(cls):
    cls.conn.rollback()

  @classmethod
  def __close(cls):
    cls.conn.close()
  
  @classmethod
  def __reset(cls, app):
    app.config["CONN"] = None

  @classmethod
  def execute(cls, app, callback):
    try:
      cls.__get_conn(app)
      app.logger.debug("Obtained DB connect from app.config['CONN'], will be running in transaction ...")
      callback()
      cls.__commit()
    except sqlite3.Error as e:
      app.logger.error("Failed to execute callback in DBT: %s", e)
      cls.__rollback()
    finally:
      cls.__reset(app)
