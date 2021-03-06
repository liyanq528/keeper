import os

from flask import Flask, current_app

def create_app(test_config=None):
  #create and configure the app
  app = Flask(__name__, instance_relative_config=True)
  app.logger.debug("Instance path: %s" % (app.instance_path))
  app.config.from_mapping(
    DATABASE=os.path.join(app.instance_path, 'keeper.sqlite'),
  )
  app.config.from_json(os.path.join(app.instance_path, 'config.json'), silent=True)
  #ensure the instance folder exists
  try:
    os.makedirs(app.instance_path)
  except OSError:
    pass
    
  from keeper import db
  db.init_app(app)

  from keeper import vm
  app.register_blueprint(vm.bp)

  from keeper import handler
  app.register_blueprint(handler.bp)

  from keeper import integration
  app.register_blueprint(integration.bp)
  
  from keeper import assistant
  app.register_blueprint(assistant.bp)

  return app

def get_info(key):
  return current_app.config['SETUP'][key]