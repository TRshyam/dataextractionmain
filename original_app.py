import os
from re import template
import shutil
from flask import Flask, redirect, url_for, request, flash,jsonify,abort
from flask import render_template
from flask import send_file
from flask_login import UserMixin,logout_user, current_user,login_user, LoginManager,login_required
from wtforms import StringField, PasswordField, SubmitField,MultipleFileField
from wtforms.validators import InputRequired, Length, ValidationError
from pdf2image import convert_from_path
from wtforms import FileField, SubmitField,MultipleFileField
from werkzeug.utils import secure_filename
from wtforms.validators import InputRequired
from flask_wtf import FlaskForm
from DataExtract import Main,MainImg
import jwt
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import datetime
import base64
from dateutil import parser

import socket
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Cordinates.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['SECRET_KEY'] = 'supersecretkeybkiran'
app.config['UPLOAD_FOLDER'] = './upload'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return tbl_user.query.get(int(user_id))


class tbl_user(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    Name= db.Column(db.String(20), nullable=False)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    status = db.Column(db.Integer)
    dateformat=db.Column(db.String(80), nullable=False,default="No")
    Date_time=db.Column(db.DateTime,default=datetime.datetime.utcnow)
    ip=db.Column(db.String(20),default='None')
    data=db.relationship('Cordinate_Data',backref='author', lazy=True)
    

    def __repr__(self)->str:
        return '<tbl_user %r>' % self.User_Name

class Cordinate_Data(UserMixin,db.Model):
    cord_id=db.Column(db.Integer,primary_key=True)
    Tem_name=db.Column(db.String(80), nullable=False)
    Tem_format=db.Column(db.String(80), nullable=False)
    cordinates=db.Column(db.Text)
    Date=db.Column(db.String(80), nullable=False)
    Time=db.Column(db.String(80), nullable=False)
    Day=db.Column(db.String(80), nullable=False)
    tempimage=db.Column(db.Text)
    user_id=db.Column(db.Integer, db.ForeignKey('tbl_user.id'),nullable=False)
   
    def __repr__(self)->str:
        return f"{self.cord_id}"


class UploadFileForm(FlaskForm):
    jsonfile = FileField("jsonfile")
    file=MultipleFileField("file",validators=[InputRequired()])
#registration flask form
class RegisterForm(FlaskForm):
    Name = StringField(validators=[
                             InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Name"})
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Register')

    def validate_username(self, username):
        existing_user_username = tbl_user.query.filter_by(
            username=username.data).first()
        if existing_user_username:
            raise ValidationError(
                'That username already exists. Please choose a different one.')

#login flask form
class LoginForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Login')

#check token valid or not
def token_required(f):
    @wraps(f)
    def decorated(*args,**kwargs):
        token=request.args.get('token')
        if not token:
            return render_template("alert.html",message="Token is missing")
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            
        except:
            return render_template("alert.html",message="Token is invalid")
        return f(*args,**kwargs)
    return decorated



#registration
@ app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        hostname=socket.gethostname()
        IPadd=socket.gethostbyname(hostname)
        new_user = tbl_user(Name=form.Name.data,username=form.username.data, password=hashed_password,status=0,ip=str(IPadd))
        db.session.add(new_user)
        db.session.commit()
           
        return redirect(url_for('login'))
   
        
    return render_template('register.html', form=form)



#login
@app.route('/', methods=["GET","POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = tbl_user.query.filter_by(username=form.username.data).first()
    
        hostname=socket.gethostname()
        IPadd=socket.gethostbyname(hostname)
        if user:
            if user.ip=='None':
                user.ip=str(IPadd)
                db.session.add(user)
                db.session.commit()
                return redirect('/')
            elif user.ip!=IPadd:
                abort(400,"You cannot access this application, contact to owner")
            
            elif bcrypt.check_password_hash(user.password, form.password.data)and user.ip==str(IPadd):
                login_user(user)
                token=jwt.encode({'user':form.username.data,'exp':datetime.datetime.utcnow()+datetime.timedelta(minutes=60)},app.config['SECRET_KEY'])
                return redirect(url_for('dashboard',token=[token]))
        else:
            flash('please enter correct details')
    return render_template('Login.html', form=form)



@app.route('/dashboard',methods = ['GET', 'POST'])
@token_required
@login_required
def dashboard():
    token=request.args.get('token')
    app.config["IMAGES"] = 'images'
    app.config["LABELS"] = []
    app.config["uploaded_files"]=[]
    app.config["TEMP_NAME"]=[]
    form = UploadFileForm()
    if request.method == 'POST':
        files = form.file.data
        print(files)
        if 'file' not in request.files:
            flash('No files selected')
            return redirect(url_for('dashboard',token=[token]))
        try:
            shutil.rmtree('./images')
            if os.path.exists("out.csv"):
                os.remove("out.csv")
            
            shutil.rmtree('./upload')
            shutil.rmtree('./jsonfile')
        except:
            pass
        os.mkdir('./images')
        os.mkdir('./upload')
        os.mkdir('./jsonfile')
        app.config["OUT"] = "out.csv"
        with open("out.csv",'w') as csvfile:
              csvfile.write("image,id,name,xMin,xMax,yMin,yMax,Format\n")
        
        files = request.files.getlist("file")
        tmp = request.form.get("Temp_name")
        print(tmp)
        app.config["TEMP_NAME"].insert(0,tmp)
  
       
        for f in files:
            f.save(os.path.join('./images', f.filename))
            with open(os.path.join('./images', f.filename), "rb") as pdf_file:
                 app.config["TEMP_Imagecode"]=base64.b64encode(pdf_file.read()).decode("UTF")
                 
            
            extention=os.path.splitext(os.path.join('./images', f.filename))[1]
            if extention in ['.jpg','.png','.tiff','.tif']:
                  app.config["uploaded_files"].append(f.filename)
                  app.config["TEMP_NAME"].insert(1,'Image')
            elif extention in ['.pdf','.PDF']:
                #------new code start
                app.config["TEMP_NAME"].insert(1,'Pdf')
                pages=convert_from_path(os.path.join('./images', f.filename),poppler_path=r"D:\tmp\DEA03Jan2022\DEA\poppler-0.67.0_x86\bin")
                path=os.path.join("./images")
                os.remove(f'./images/{f.filename}')
                count=0
                for page in pages:
                    count+=1
                    jpg=path+"/"+str(count)+".jpg"
                    page.save(jpg,'JPEG')
                    app.config["uploaded_files"].append(count)
                #-----new code end
        app.config["uploaded_files"].sort()   
        for (dirpath, dirnames, filenames) in os.walk(app.config["IMAGES"]):
            files = filenames
            break
        app.config["FILES"] = files
        return redirect(f'/tagger?token={token}', code=302)
    else:
        Data=Cordinate_Data.query.filter_by(user_id=current_user.id).all()
      
        d=tbl_user.query.filter_by(id=current_user.id).first()
        return render_template("Dashboard.html",token=token,current_user=current_user,Data=Data,status=int(d.status),total=len(Data),form=form)



@app.route('/tagger',methods = ['GET'])
@token_required
@login_required
def tagger():
    token=request.args.get('token')
    done=request.args.get('done')
    if (done == "Yes"):
        with open(app.config["OUT"],'a') as f:
            for label in app.config["LABELS"]:
                f.write(image + "," +
                label["id"] + "," +
                label["name"] + "," +
                str(round(float(label["xMin"]))) + "," +
                str(round(float(label["xMax"]))) + "," +
                str(round(float(label["yMin"]))) + "," +
                str(round(float(label["yMax"]))) + "," +
                str(label["dformat"]) + "\n")
                #coTox(image,label["id"],label["name"],round(float(label["xMin"])),round(float(label["yMin"])),round(float(label["xMax"])),round(float(label["yMax"])))
        with open(app.config["OUT"],'r') as s:
            data=s.read()
        x = datetime.datetime.now()
        cordinates=data
        templateName=app.config["TEMP_NAME"][0]
        Template_format=app.config["TEMP_NAME"][1]
        print(Template_format)
        current_time = x.strftime("%I:%M:%S %p")
        Date=f"{x.day}/{x.month}/{x.year}"
        Day=x.strftime("%A")
        adddata=Cordinate_Data(cordinates=cordinates,user_id=current_user.id,Tem_name=templateName,Date=Date,Time=current_time,Day=Day,tempimage=app.config["TEMP_Imagecode"],Tem_format=Template_format)
        db.session.add(adddata)
        db.session.commit()
        return redirect(url_for('upload',token=[token]))
    directory = app.config["IMAGES"]
    #image = app.config["FILES"][app.config["HEAD"]]
    #image=str(app.config["HEAD"])+".jpg"
    if type(app.config["uploaded_files"][app.config["HEAD"]]) == str:
        image=str(app.config["uploaded_files"][app.config["HEAD"]])
    else:
        image=str(app.config["uploaded_files"][app.config["HEAD"]])+".jpg"
    labels = app.config["LABELS"]
    not_end = not(app.config["HEAD"] == len(app.config["FILES"])-1)
    d=tbl_user.query.filter_by(id=current_user.id).first()
    return render_template('tagger.html', not_end=not_end, directory=directory, image=image, labels=labels, head=app.config["HEAD"]+1, len=len(app.config["FILES"]),token=token,status=int(d.status))



@app.route('/next')
@token_required
@login_required
def next():
    token=request.args.get('token')
    done=request.args.get('done')
    
    #image = app.config["FILES"][app.config["HEAD"]]
    #image=str(app.config["HEAD"])+".jpg"
    image=str(app.config["uploaded_files"][app.config["HEAD"]])+".jpg"
    app.config["HEAD"] = app.config["HEAD"] + 1
    with open(app.config["OUT"],'a') as f:
        for label in app.config["LABELS"]:
            f.write(image + "," +
            label["id"] + "," +
            label["name"] + "," +
            str(round(float(label["xMin"]))) + "," +
            str(round(float(label["xMax"]))) + "," +
            str(round(float(label["yMin"]))) + "," +
            str(round(float(label["yMax"]))) + "," +
            str(label["dformat"]) + "\n")
            #coTox(image,label["id"],label["name"],round(float(label["xMin"])),round(float(label["yMin"])),round(float(label["xMax"])),round(float(label["yMax"])))
    app.config["LABELS"] = []
    return redirect(url_for('tagger',token=[token],done=[done]))



@app.route('/previous')
@token_required
@login_required
def previous():
    token=request.args.get('token')
    done=request.args.get('done')
    #image = app.config["FILES"][app.config["HEAD"]]
    #image=str(app.config["HEAD"])+".jpg"
    image=str(app.config["uploaded_files"][app.config["HEAD"]])+".jpg"
    
    with open(app.config["OUT"],'a') as f:
        for label in app.config["LABELS"]:
            f.write(image + "," +
            label["id"] + "," +
            label["name"] + "," +
            str(round(float(label["xMin"]))) + "," +
            str(round(float(label["xMax"]))) + "," +
            str(round(float(label["yMin"]))) + "," +
            str(round(float(label["yMax"]))) + "," +
            str(label["dformat"]) + "\n")
            #coTox(image,label["id"],label["name"],round(float(label["xMin"])),round(float(label["yMin"])),round(float(label["xMax"])),round(float(label["yMax"])))
    app.config["LABELS"] = []
    
    app.config["HEAD"] = app.config["HEAD"] - 1
    return redirect(url_for('tagger',token=[token],done=[done]))


@app.route('/add/<id>')
@token_required
@login_required
def add(id):
    token=request.args.get('token')
    xMin = request.args.get("xMin")
    xMax = request.args.get("xMax")
    yMin = request.args.get("yMin")
    yMax = request.args.get("yMax")
    app.config["LABELS"].append({"id":id, "name":"", "xMin":xMin, "xMax":xMax, "yMin":yMin, "yMax":yMax,"dformat":""})
    return redirect(url_for('tagger',token=[token]))


@app.route('/remove/<id>')
@token_required
@login_required
def remove(id):
    token=request.args.get('token')
    index = int(id) - 1
    del app.config["LABELS"][index]
    for label in app.config["LABELS"][index:]:
        label["id"] = str(int(label["id"]) - 1)
    return redirect(url_for('tagger',token=[token]))


@app.route('/label/<id>')
def label(id):
    token=request.args.get('token')
    name = request.args.get("name")
    dformat = request.args.get("dformat")
    app.config["LABELS"][int(id) - 1]["name"] = name
    app.config["LABELS"][int(id) - 1]["dformat"] = dformat
    return redirect(url_for('tagger',token=[token]))


@app.route('/image/<f>')
def images(f):
    images = app.config["IMAGES"]
    return send_file(images +'/'+f)



@app.route('/upload',methods = ['GET', 'POST'])
@token_required
@login_required
def upload():
    token=request.args.get('token')
    app.config["HEAD"] = 0
    form = UploadFileForm()
    if request.method == 'POST':
        files = form.file.data
        jsonfile = form.jsonfile.data
        option=request.form['option']
        if option=="2":
            jsonfile.save(os.path.join(os.path.abspath(os.path.dirname(__file__)),'./jsonfile',secure_filename(jsonfile.filename)))
        app.config["Data"]=[]
        for file in files:
            folderpath=os.path.join(os.path.abspath(os.path.dirname(__file__)),app.config['UPLOAD_FOLDER'],secure_filename(file.filename))
            file.save(os.path.join(os.path.abspath(os.path.dirname(__file__)),app.config['UPLOAD_FOLDER'],secure_filename(file.filename))) # Then save the file
            #print(file.filename)
            extention=os.path.splitext(file.filename)[1]
            #print(os.path.splitext(file.filename)[0],extention)
            if extention in ['.pdf','.PDF']:
                #------new code start
                pages=convert_from_path(folderpath,poppler_path=r"D:\tmp\DEA03Jan2022\DEA\poppler-0.67.0_x86\bin")
                path=os.path.join("./images")
                #os.remove(f'./images/{file.filename}')
                count=0
                for page in pages:
                    count+=1
                    jpg=path+"/"+str(count)+".jpg"
                    page.save(jpg,'JPEG')
                    data=Main(str(count)+".jpg",file.filename,count,option) 
                    app.config["Data"].append(data)
                
                #-----new code end
            elif extention in ['.jpg','.png','.jpeg','.tiff','.tif']:
                page_count=1
                for f in os.listdir('./upload'):
                    
                    data=MainImg(os.path.join('./upload',f),file.filename,page_count,option)
                   
                    os.remove(os.path.join('./upload',f))
                    app.config["Data"].append(data)
        return redirect(url_for('download',token=[token]))
    try:
        shutil.rmtree('./jsonfile')
        shutil.rmtree('./images')
        flash('Please wait for converting')
        os.mkdir('./jsonfile')
        os.mkdir('./images')
        
    except:
        pass
    d=tbl_user.query.filter_by(id=current_user.id).first()
    return render_template("upload.html",form=form,token=token,status=int(d.status))


@app.route("/download", methods=['POST','GET'])
@token_required
@login_required
def download():
    token=request.args.get('token')
    d=tbl_user.query.filter_by(id=current_user.id).first()
    Data=[]
    print(app.config["Data"])
    for data in app.config["Data"]:
        for j in data.values():
            if j["Format"]=="Date":

                
                if d.dateformat!="No":
                    try:
                        dt=parser.parse(j["label_data"])
                        date=datetime.datetime.strftime(dt,d.dateformat)
                        j["label_data"]=date
                    except:
                        pass
                else:
                    j["label_data"]=j["label_data"]
                    
            

            Data.append(j)
    return render_template('JsonData.html',data=Data,token=token,status=int(d.status))


@app.route("/apply/<int:id>")
@token_required
@login_required
def applyonfolder(id):
    token=request.args.get('token')
    data=Cordinate_Data.query.filter_by(cord_id=id,user_id=current_user.id).first()
    with open("out.csv",'w') as f:
        f.write(data.cordinates)
    return redirect(url_for('upload',token=[token]))




@app.route("/setting", methods=['POST','GET'])
@token_required
@login_required
def setting():
    token=request.args.get('token')
    d=tbl_user.query.filter_by(id=current_user.id).first()
    return render_template("setting.html",token=token,status=int(d.status),dateformat=d.dateformat)



@app.route("/profile", methods=['POST','GET'])
@token_required
@login_required
def profile():
    token=request.args.get('token')
    d=tbl_user.query.filter_by(id=current_user.id).first()
    tatal=Cordinate_Data.query.filter_by(user_id=current_user.id).count()
    return render_template("profile.html",token=token,data=d,total=tatal)



@app.route("/HelpChange", methods=['POST','GET'])
@token_required
@login_required
def Helpchange():
    token=request.args.get('token')
    status=request.args.get('status')
    d=tbl_user.query.filter_by(id=current_user.id).first()
    d.status=status
    db.session.add(d)
    db.session.commit()
    print("yes")
    return redirect(url_for('setting',token=[token]))


@app.route("/changedate", methods=['POST','GET'])

def FormatChange():
    print("hello"*50)
    token=request.args.get('token')
    dateformat=request.args.get('dateformat')
    d=tbl_user.query.filter_by(id=current_user.id).first()
    d.dateformat=str(dateformat)
    db.session.add(d)
    db.session.commit()
    print("yes")
    return redirect(url_for('setting',token=[token]))
    
       

    


@app.route("/delete/<int:id>")
@token_required
@login_required
def delete(id):
    token=request.args.get('token')
    d=Cordinate_Data.query.filter_by(cord_id=id,user_id=current_user.id).first()
    db.session.delete(d)
    db.session.commit()
    return redirect(url_for('dashboard',token=[token]))



@app.route("/logout")
@token_required
@login_required
def logout():
    logout_user()
    return redirect("/")



if __name__ == "__main__":
    
    app.config["IMAGES"] = 'images'
    app.config["LABELS"] = []
    app.config["HEAD"] = 0
    app.config["uploaded_files"]=[]
    app.config["TEMP_NAME"]=[]
    app.config["TEMP_Imagecode"]=""
    app.config["Data"]=[]
    with app.app_context():
        db.create_all()
    app.run(debug=True,port=3000)