from flask import Blueprint,current_app
vote = Blueprint("vote",__name__,template_folder='templates')#static folder and template folder are set here to avoid ambiguity

from studio.vote import views,admin