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
from PIL import Image

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
    print("In the cordinate data")
    print("cord_id",cord_id,"Tem_name",Tem_name,"Tem_format",Tem_format,"cordinates",cordinates,"Date",Date,"Time",Time,"Day",Day,"tempimage",tempimage,"user_id",user_id)
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


@app.route('/dashboard', methods=['GET', 'POST'])
@token_required
@login_required
def dashboard():
    token = request.args.get('token')
    app.config["IMAGES"] = 'images'
    app.config["LABELS"] = []
    app.config["uploaded_files"] = []
    app.config["TEMP_NAME"] = []
    form = UploadFileForm()

    if request.method == 'POST':
        files = form.file.data
        print(files)

        if 'file' not in request.files:
            flash('No files selected')
            return redirect(url_for('dashboard', token=[token]))

        try:
            # Cleanup previous directories and files
            shutil.rmtree('./images')
            if os.path.exists("out.csv"):
                os.remove("out.csv")
            
            shutil.rmtree('./upload')
            shutil.rmtree('./jsonfile')
        except:
            pass

        # Create new directories for uploads and output
        os.mkdir('./images')
        os.mkdir('./upload')
        os.mkdir('./jsonfile')

        # Create CSV for output data
        app.config["OUT"] = "out.csv"
        with open("out.csv", 'w') as csvfile:
            csvfile.write("image,id,name,xMin,xMax,yMin,yMax,Format\n")

        # Get uploaded files and the temporary name
        files = request.files.getlist("file")
        tmp = request.form.get("Temp_name")
        print(tmp)
        app.config["TEMP_NAME"].insert(0, tmp)

        for f in files:
            # Extract filename without the path prefix if it exists
            filename = f.filename
            if '/' in filename:
                filename = filename.split('/')[-1]  # Get the part after the last '/'
            elif '\\' in filename:  # For Windows paths
                filename = filename.split('\\')[-1]  # Get the part after the last '\\'
            
            print("file name", filename)  # Now it will print only the file name without the path

            # Save the file with the correct filename
            filepath = os.path.join('images', filename)
            f.save(filepath)
            
            # Convert .tif or .tiff files to .png
            extention = os.path.splitext(filepath)[1].lower()
            if extention in ['.tif', '.tiff']:
                with Image.open(filepath) as img:
                    new_filename = os.path.splitext(filename)[0] + '.png'
                    new_filepath = os.path.join('images', new_filename)
                    img.save(new_filepath, 'PNG')
                os.remove(filepath)  # Remove the original .tif or .tiff file
                filename = new_filename  # Update the filename to the new .png file

            # Handle image or PDF files differently
            with open(os.path.join('./images', filename), "rb") as file:
                app.config["TEMP_Imagecode"] = base64.b64encode(file.read()).decode("UTF")

            # Handle image files
            if extention in ['.jpg', '.png', '.tiff', '.tif']:
                app.config["uploaded_files"].append(filename)
                app.config["TEMP_NAME"].insert(1, 'Image')

            # Handle PDF files
            elif extention in ['.pdf', '.PDF']:
                app.config["TEMP_NAME"].insert(1, 'Pdf')
                pages = convert_from_path(os.path.join('./images', filename), poppler_path="poppler/bin")
                path = os.path.join("./images")
                os.remove(f'./images/{filename}')
                
                count = 0
                for page in pages:
                    count += 1
                    jpg = path + "/" + str(count) + ".jpg"
                    page.save(jpg, 'JPEG')
                    app.config["uploaded_files"].append(count)
        
        # Sort the uploaded files
        app.config["uploaded_files"].sort()

        # Get files from the images directory
        for (dirpath, dirnames, filenames) in os.walk(app.config["IMAGES"]):
            files = filenames
            break
        
        app.config["FILES"] = files
        return redirect(f'/tagger?token={token}', code=302)

    else:
        Data = Cordinate_Data.query.filter_by(user_id=current_user.id).all()
        d = tbl_user.query.filter_by(id=current_user.id).first()
        return render_template("Dashboard.html", token=token, current_user=current_user, Data=Data, status=int(d.status), total=len(Data), form=form)




@app.route('/tagger', methods=['GET'])
@token_required
@login_required
def tagger():
    print("its in tagger")
    token = request.args.get('token')
    done = request.args.get('done')
    
    if done == "Yes":
        with open(app.config["OUT"], 'a') as f:
            for label in app.config["LABELS"]:
                f.write(image + "," +
                        label["id"] + "," +
                        label["name"] + "," +
                        str(round(float(label["xMin"]))) + "," +
                        str(round(float(label["xMax"]))) + "," +
                        str(round(float(label["yMin"]))) + "," +
                        str(round(float(label["yMax"]))) + "," +
                        str(label["dformat"]) + "\n")
        with open(app.config["OUT"], 'r') as s:
            data = s.read()
        
        x = datetime.datetime.now()
        cordinates = data
        templateName = app.config["TEMP_NAME"][0]
        Template_format = app.config["TEMP_NAME"][1]
        current_time = x.strftime("%I:%M:%S %p")
        Date = f"{x.day}/{x.month}/{x.year}"
        Day = x.strftime("%A")
        
        adddata = Cordinate_Data(
            cordinates=cordinates,
            user_id=current_user.id,
            Tem_name=templateName,
            Date=Date,
            Time=current_time,
            Day=Day,
            tempimage=app.config["TEMP_Imagecode"],
            Tem_format=Template_format
        )
        print("adddata", adddata)  # Verify the object is created properly
        
        try:
            db.session.add(adddata)
            db.session.commit()
            print("Data saved successfully")
        except Exception as e:
            db.session.rollback()
            print(f"Error occurred while saving data: {e}")
        
        # Verify the data is saved
        latest_data = Cordinate_Data.query.order_by(Cordinate_Data.cord_id.desc()).first()
        if latest_data:
            print("Latest data in the database:", latest_data)
        else:
            print("Failed to save data.")
        
        return redirect(url_for('upload', token=[token]))
    
    directory = app.config["IMAGES"]
    if type(app.config["uploaded_files"][app.config["HEAD"]]) == str:
        image = str(app.config["uploaded_files"][app.config["HEAD"]])
    else:
        image = str(app.config["uploaded_files"][app.config["HEAD"]]) + ".jpg"
    
    labels = app.config["LABELS"]
    not_end = not(app.config["HEAD"] == len(app.config["FILES"]) - 1)
    d = tbl_user.query.filter_by(id=current_user.id).first()
    return render_template('tagger.html', not_end=not_end, directory=directory, image=image, labels=labels, head=app.config["HEAD"] + 1, len=len(app.config["FILES"]), token=token, status=int(d.status))


@app.route('/next')
@token_required
@login_required
def next():
    token = request.args.get('token')
    done = request.args.get('done')

    # If HEAD exceeds the number of uploaded files, reset to 0 to avoid index out of range
    if app.config["HEAD"] >= len(app.config["uploaded_files"]):
        app.config["HEAD"] = 0  # Reset the HEAD to 0

    # Get the current image based on the HEAD index
    image = str(app.config["uploaded_files"][app.config["HEAD"]]) + ".jpg"

    # Increment HEAD for the next image, making sure not to exceed the length of the list
    app.config["HEAD"] = (app.config["HEAD"] + 1) % len(app.config["uploaded_files"])

    # Write the label data to the output CSV
    with open(app.config["OUT"], 'a') as f:
        for label in app.config["LABELS"]:
            f.write(image + "," +
                    label["id"] + "," +
                    label["name"] + "," +
                    str(round(float(label["xMin"]))) + "," +
                    str(round(float(label["xMax"]))) + "," +
                    str(round(float(label["yMin"]))) + "," +
                    str(round(float(label["yMax"]))) + "," +
                    str(label["dformat"]) + "\n")
    
    # Clear LABELS for the next image
    app.config["LABELS"] = []

    # Redirect back to the tagger with the token and done status
    return redirect(url_for('tagger', token=[token], done=[done]))



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

@app.route('/upload', methods=['GET', 'POST'])
@token_required
@login_required
def upload():
    token = request.args.get('token')
    app.config["HEAD"] = 0
    form = UploadFileForm()

    if request.method == 'POST':
        files = form.file.data
        jsonfile = form.jsonfile.data
        option = request.form['option']

        # Ensure the directories exist
        jsonfile_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'jsonfile')
        images_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'images')

        try:
            if not os.path.exists(jsonfile_dir):
                os.makedirs(jsonfile_dir)
            if not os.path.exists(images_dir):
                os.makedirs(images_dir)
        except Exception as e:
            print(f"Error during directory setup: {e}")

        if option == "2":
            jsonfile_path = os.path.join(jsonfile_dir, secure_filename(jsonfile.filename))
            try:
                jsonfile.save(jsonfile_path)
                print(f"JSON file saved at: {jsonfile_path}")
            except Exception as e:
                print(f"Error saving JSON file: {e}")

        app.config["Data"] = []
        print("Initialized app.config[\"Data\"] as an empty list.")

        for file in files:
            folderpath = os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
            try:
                file.save(folderpath)
                print(f"File saved at: {folderpath}")

                extention = os.path.splitext(file.filename)[1].lower()
                print(f"File extension: {extention}")

                if extention in ['.pdf']:
                    pages = convert_from_path(folderpath, poppler_path="poppler/bin")
                    count = 0
                    for page in pages:
                        count += 1
                        jpg = os.path.join(images_dir, str(count) + ".jpg")
                        page.save(jpg, 'JPEG')
                        print(f"Page saved as: {jpg}")

                        data = Main(str(count) + ".jpg", file.filename, count, option)
                        app.config["Data"].append(data)
                        print(f"Appended data from PDF page: {data}")

                elif extention in ['.jpg', '.png', '.jpeg', '.tiff', '.tif']:
                    page_count = 1
                    for f in os.listdir(os.path.join(os.path.abspath(os.path.dirname(__file__)), app.config['UPLOAD_FOLDER'])):
                        image_path = os.path.join(app.config['UPLOAD_FOLDER'], f)
                        data = MainImg(image_path, file.filename, page_count, option)
                        app.config["Data"].append(data)
                        print(f"Appended data from image: {data}")

                        os.remove(image_path)
                        print(f"Removed file: {image_path}")

            except Exception as e:
                print(f"Error processing file: {e}")

        print("Final app.config[\"Data\"]:", app.config["Data"])
        return redirect(url_for('download', token=token))

    try:
        if os.path.exists(jsonfile_dir):
            shutil.rmtree(jsonfile_dir)
        if os.path.exists(images_dir):
            shutil.rmtree(images_dir)
        os.makedirs(jsonfile_dir)
        os.makedirs(images_dir)
        flash('Please wait for converting')
    except Exception as e:
        print(f"Error during directory cleanup or creation: {e}")

    d = tbl_user.query.filter_by(id=current_user.id).first()
    return render_template("upload.html", form=form, token=token, status=int(d.status))


@app.route("/download", methods=['POST', 'GET'])
@token_required
@login_required
def download():
    token = request.args.get('token')
    d = tbl_user.query.filter_by(id=current_user.id).first()
    Data = []
    print("app.config[\"Data\"]:", app.config["Data"])

    if not isinstance(app.config["Data"], list):
        print("app.config[\"Data\"] is not a list")
        return render_template('JsonData.html', data=Data, token=token, status=int(d.status))

    for data in app.config["Data"]:
        if not isinstance(data, dict):
            print(f"Unexpected data structure: {data}")
            continue
        for j in data.values():
            if not isinstance(j, dict):
                print(f"Unexpected value in data: {j}")
                continue
            if j.get("Format") == "Date":
                if d.dateformat != "No":
                    try:
                        dt = parser.parse(j["label_data"])
                        date = datetime.datetime.strftime(dt, d.dateformat)
                        j["label_data"] = date
                    except Exception as e:
                        print(f"Date parsing error: {e}")
                else:
                    j["label_data"] = j["label_data"]
            Data.append(j)

    print("Data", Data)
    return render_template('JsonData.html', data=Data, token=token, status=int(d.status))


@app.route("/apply/<int:id>")
@token_required
@login_required
def applyonfolder(id):
    token=request.args.get('token')
    data=Cordinate_Data.query.filter_by(cord_id=id,user_id=current_user.id).first()
    with open("out.csv",'w') as f:
        f.write(data.cordinates)
        print("data.cordinates",data.cordinates)
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
    app.run(debug=True,port=5000)



#tagger.html out.csv JsonData.html next