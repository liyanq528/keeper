from flask import (
  Blueprint, request,  jsonify, current_app, abort, Response, url_for
)

from keeper.db import get_vm
from keeper.manager import KeeperManager, KeeperException
from keeper.util import SubTaskUtil
from keeper.model import VM

bp = Blueprint('vm', __name__, url_prefix="/api/v1")

@bp.route('/vm', methods=["GET", "POST"])
def vm():
  vm_name = request.args.get('name', None)
  if vm_name is None:
    return abort(400, "VM name is required.")
  if request.method == "GET":
    info = get_vm(vm_name)
    if info is None:
      return abort(404, "No VM found with name: %s" % vm_name)
    return jsonify(dict(info))
  elif request.method == "POST":
    username = request.args.get('username', None)
    if not username:
      return abort(400, 'Username is required.')
    project_name = request.args.get('project_name', None)
    if not project_name:
      return abort(400, 'Project name is required.')
    ip_provision_id = request.args.get('ip_provision_id', None)
    if not ip_provision_id:
      return abort(400, "IP provision ID is required.")
    pipeline_id = request.args.get('pipeline_id', None)
    if not pipeline_id:
      return abort(400, "Pipeline ID is required.")
    vm_conf = request.get_json()
    if 'vm_box' not in vm_conf:
      return abort(400, 'VM box is required.')
    if 'vm_ip' not in vm_conf:
      return abort(400, 'VM IP is required.')
    if 'vm_memory' not in vm_conf:
      return abort(400, 'VM memory is required.')     
    if 'runner_tag' not in vm_conf:
      return abort(400, 'Runner tag is required.')
    try:
      current = current_app._get_current_object()
      def callback():
        manager = KeeperManager(current, vm_name)
        project = KeeperManager.resolve_project(username, project_name, current)
        runner_token = KeeperManager.resolve_runner_token(username, project_name, current)
        manager.generate_vagrantfile(runner_token, vm_conf)
        manager.copy_vm_files()
        current.logger.debug(manager.create_vm())
        info = manager.get_vm_info()
        vm = VM(vm_id=info.id, vm_name=vm_name, target="AUTOMATED", keeper_url="N/A")
        runner = KeeperManager.register_project_runner(username, project_name, vm_name, vm, snapshot=None, app=current_app)
        KeeperManager.register_ip_runner(ip_provision_id, runner.runner_id, pipeline_id, current)
      SubTaskUtil.set(current_app, callback).start()
      return jsonify(message="VM: %s has being created." % vm_name)
    except KeeperException as e:
      return abort(e.code, e.message)

@bp.route("/vm/info/<path:vm_name>", methods=["GET", "DELETE"])
def vm_info(vm_name):
  if vm_name is None:
    return abort(400, "VM name is required.")
  try:
    manager = KeeperManager(current_app, vm_name)
    info = manager.get_vm_info()
    if request.method == "GET":
      return jsonify(vm_id=info.id, vm_name=vm_name, vm_provider=info.provider,
      vm_status=info.status, vm_directory=info.directory)
    elif request.method == "DELETE":
      project_name = request.args.get("project_name", None)
      if not project_name:
        return abort(400, "Project name is required.")
      def callback():
        manager.force_delete_vm()
        manager.unregister_runner_by_name(vm_name, current_app)
      SubTaskUtil.set(current_app, callback).start()
      return jsonify(message="VM: %s is being deleted." % vm_name)
  except KeeperException as e:
    return abort(e.code, e.message)
