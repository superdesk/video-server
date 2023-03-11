import bson
from flask import current_app as app
from flask.views import MethodView as FlaskMethodView
from werkzeug.exceptions import NotFound


class MethodView(FlaskMethodView):
    """
    Enhance default flask MethodView
    """

    def __init__(self, *args, **kwargs):
        self._project_id = None
        self._project_doc = None
        super().__init__(*args, **kwargs)

    def dispatch_request(self, *args, **kwargs):
        """
        Automatically preload project from db if `project_id` is in request.
        """
        if 'project_id' in kwargs:
            self._project_id = kwargs['project_id']

        return super().dispatch_request(*args, **kwargs)

    @staticmethod
    def _get_project_or_404(project_id):
        try:
            doc = app.mongo.db.projects.find_one({'_id': bson.ObjectId(project_id)})
        except bson.errors.InvalidId as e:
            raise NotFound(f"Project with id '{project_id}' was not found.")

        if not doc:
            raise NotFound(f"Project with id '{project_id}' was not found.")
        return doc

    @property
    def project(self):
        if self._project_doc:
            return self._project_doc
        elif self._project_id:
            self._project_doc = self._get_project_or_404(self._project_id)
            return self._project_doc
        else:
            return None

    @project.setter
    def project(self, project_doc):
        self._project_doc = project_doc
