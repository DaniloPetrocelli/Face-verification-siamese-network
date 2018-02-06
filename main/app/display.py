from flask import Flask, render_template, request
import os
from torch.autograd import Variable
import torch.nn.functional as F
from PIL import Image, ImageChops
import torchvision.transforms as transforms
import torch
from siameseContrastive import SiameseNetwork
from appDataset import AppDataset
from appDatasetDuplicates import AppDatasetDuplicates
from torch.utils.data import DataLoader,Dataset
import numpy as np
import zipfile
import os
import pandas as pd

app = Flask(__name__)
app.config['CACHE_TYPE'] = "null"

pre_path = "static/upload/pre/temp"
post_path = "static/upload/post/temp"

# Load model
net = torch.load('model.pt', map_location = lambda storage, loc:storage).eval()
# net = net.cpu().double().eval()
net = torch.load('model_duplicate_pre.pt')
net_pre = torch.load('model_duplicate_pre.pt')
net_post = torch.load('model_duplicate_post.pt')

@app.route("/")
def display():
    return render_template('/display.html')

@app.route("/display-directory")
def display_directory():
    return render_template('/display-directory.html')

@app.route("/upload-directory", methods=['POST'])
def upload_directory():
    
    # Get Pre and Post Directories
    pre = request.files['pre-directory']
    post = request.files['post-directory']

    pref = os.path.join(pre_path, "pre-directory.zip")
    postf = os.path.join(post_path, "pre-directory.zip")

    pre.save(pref)
    post.save(postf)

    # Extract Zip files
    zip_ref = zipfile.ZipFile(pref, 'r')
    zip_ref.extractall("static/upload/dir/pre")
    zip_ref.close()

    zip_ref = zipfile.ZipFile(postf, 'r')
    zip_ref.extractall("static/upload/dir/post")
    zip_ref.close()

    # Delete Zip Files
    os.remove(pref)
    os.remove(postf)

    # Open 
    for x in os.listdir('static/upload/dir/pre'):
        if os.path.isdir('static/upload/dir/pre/'+str(x)):
            dirpre='static/upload/dir/pre/'+str(x)
    
    for x in os.listdir('static/upload/dir/post/'):
        if os.path.isdir('static/upload/dir/post/'+str(x)):
            dirpost='static/upload/dir/post/'+str(x)
    
    listpre = os.listdir(dirpre)
    listpost = os.listdir(dirpost)

    distances = []

    for x in range (0,len(listpre)):

        # Create folder and move image to that folder
        os.mkdir(dirpre+"/"+str(x))
        os.mkdir(dirpost+"/"+str(x))

        pref = dirpre + "/" + str(x) + "/" + listpre[x]
        postf = dirpost + "/" + str(x) + "/" + listpost[x]

        os.rename(dirpre+"/"+listpre[x],pref)
        os.rename(dirpost+"/"+listpost[x],postf)

        im = Image.open(pref)
        im = im.resize((50, 50), Image.NEAREST)
        im.save(pref, "JPEG")
        im = Image.open(postf)
        im = im.resize((50, 50), Image.NEAREST)
        im.save(postf, "JPEG")

    # Load Images
    dataset_pre = AppDatasetDuplicates(dirpre,dirpre)
    dataloader_pre = DataLoader(dataset_pre,
                        shuffle=False,
                        num_workers=4,
                        batch_size=1)

    dataset_post = AppDatasetDuplicates(dirpost,dirpost)
    dataloader_post = DataLoader(dataset_post,
                        shuffle=False,
                        num_workers=4,
                        batch_size=1)

    dataset = AppDatasetDuplicates(dirpre,dirpost)
    dataloader = DataLoader(dataset,
                        shuffle=False,
                        num_workers=4,
                        batch_size=1)

    # Read csv here
    df_pre = pd.read_csv("static/pre_values.csv")
    df_post = pd.read_csv("static/post_values.csv")
    pre_match_img = []
    pre_match_dist = []
    pre_match_old = []
    post_match_img = []
    post_match_dist = []
    post_match_old = []
    
    for x in range(len(listpre)):
        os.rename(dirpre + "/" + str(x) + "/" + listpre[x],"/images/pre/"+listpre[x])
        os.rename(dirpost + "/" + str(x) + "/" + listpost[x],"/images/post/"+listpost[x])

        os.remove(dirpre + "/" + str(x))
        os.remove(dirpost + "/" + str(x))

        data_iter_pre = iter(dataloader_pre)
        (img0, img1) = next(data_iter_pre)

        # Calculate distance
        img0, img1 = Variable(img0).cuda(), Variable(img1).cuda()
        (img0_output_pre, img1_output)  = net_pre(img0, img1)
        for y in range(0,df_pre.count()[0]):
            euclidean_distance = F.pairwise_distance(img0_output_pre, df_pre.iloc[y][1])
            euclidean_distance = euclidean_distance.data.cpu().numpy()[0][0]
            if euclidean_distance < 1:
                pre_match_dist.append(euclidean_distance)
                pre_match_img.append("/images/pre/"+listpre[x])
                pre_match_old.append(df_pre.iloc[y][0])
        csv_pre = open("static/pre_values.csv",'a')
        csv_pre.write("images/pre/"+listpre[x]+","+img0_output_pre)
        csv_pre.close()



        data_iter_post = iter(dataloader_post)
        (img0, img1) = next(data_iter_post)

        # Calculate distance
        img0, img1 = Variable(img0).cuda(), Variable(img1).cuda()
        (img0_output_post, img1_output)  = net_post(img0, img1)
        for y in range(0,df_post.count()[0]):
            euclidean_distance = F.pairwise_distance(img0_output_post, df_post.iloc[y][1])
            euclidean_distance = euclidean_distance.data.cpu().numpy()[0][0]
            if euclidean_distance < 1:
                post_match_dist.append(euclidean_distance)
                post_match_img.append("/images/post/"+listpre[x])
                post_match_old.append(df_post.iloc[y][0])
        csv_post = open("static/post_values.csv",'a')
        csv_post.write("images/post/"+listpost[x]+","+img0_output_post)
        csv_post.close()



        data_iter = iter(dataloader)
        (img0, img1) = next(data_iter)

        # Calculate distance
        # img0, img1 = Variable(img0).cuda(), Variable(img1).cuda()
        img0, img1 = Variable(img0), Variable(img1)
        # img0 = img0.unsqueeze(0)
        (img0_output, img1_output)  = net(img0, img1)
        
        euclidean_distance = F.pairwise_distance(img0_output, img1_output)

        euclidean_distance = euclidean_distance.data.cpu().numpy()[0][0]

        distances.append(euclidean_distance)

    pre_match = [pre_match_dist,pre_match_img,pre_match_old]
    post_match = [post_match_dist,post_match_img,post_match_old]
    os.remove(dirpre)
    os.remove(dirpost)
    return str(distances[0])

@app.route("/upload", methods=['POST'])
def upload():

    # Get Pre and Post Images
    pre = request.files['pre']
    post = request.files['post']

    # Store path and name for images
    pref = os.path.join(pre_path, "PRE.jpg")
    postf = os.path.join(post_path, "POST.jpg")
    
    # Image save
    pre.save(pref)
    post.save(postf)
    
    # Check if image is Photoshopped
    cnt_post, cnt_pre = checkPhotoshop()

    # Load Images
    dataset = AppDataset()
    dataloader = DataLoader(dataset,
                        shuffle=False,
                        num_workers=4,
                        batch_size=1)

    data_iter = iter(dataloader)
    (img0, img1) = next(data_iter)


    # Calculate distance
    # img0, img1 = Variable(img0).cuda(), Variable(img1).cuda()
    img0, img1 = Variable(img0), Variable(img1)
    # img0 = img0.unsqueeze(0)
    (img0_output, img1_output)  = net(img0, img1)
        
    # img0_output
    # img1_output
    
    euclidean_distance = F.pairwise_distance(img0_output, img1_output)

    euclidean_distance = euclidean_distance.data.cpu().numpy()[0][0]

    # distances.append(euclidean_distance)
    print(euclidean_distance)

    return render_template("result-single.html", distance = euclidean_distance, cnt_post = cnt_post, cnt_pre=cnt_pre)

def checkPhotoshop():

    ORIG_POST = os.path.join(post_path, "POST.jpg")
    TEMP_POST = os.path.join(post_path, "POST-TEMP.jpg")
    ORIG_PRE = os.path.join(pre_path, "PRE.jpg")
    TEMP_PRE = os.path.join(pre_path, "PRE-TEMP.jpg")
    SCALE = 15

    original_post = Image.open(ORIG_POST)
    original_post.save(TEMP_POST, quality=90)
    temporary_post = Image.open(TEMP_POST)
    original_pre = Image.open(ORIG_PRE)
    original_pre.save(TEMP_PRE, quality=90)
    temporary_pre = Image.open(TEMP_PRE)
    
    diff_post = ImageChops.difference(original_post, temporary_post)
    d_post = diff_post.load()
    WIDTH, HEIGHT = diff_post.size
    for x in range(WIDTH):
        for y in range(HEIGHT):
            d_post[x, y] = tuple(k * SCALE for k in d_post[x, y])

    diff_post.save(post_path+"/POST-ELA.jpg")

    diff_pre = ImageChops.difference(original_pre, temporary_pre)
    d_pre = diff_pre.load()
    WIDTH, HEIGHT = diff_pre.size
    for x in range(WIDTH):
        for y in range(HEIGHT):
            d_pre[x, y] = tuple(k * SCALE for k in d_pre[x, y])

    diff_pre.save(pre_path+"/PRE-ELA.jpg")
    
    # Count the number of pixels in ELA image
    img_ela_post = np.asarray(Image.open(post_path+"/POST-ELA.jpg"))
    img_hist_post = np.histogram(img_ela_post.ravel(),256,[0,256])
    cnt_post = np.count_nonzero(img_hist_post[0])

    img_ela_pre = np.asarray(Image.open(pre_path+"/PRE-ELA.jpg"))
    img_hist_pre = np.histogram(img_ela_pre.ravel(),256,[0,256])
    cnt_pre = np.count_nonzero(img_hist_pre[0])
    
    return cnt_post, cnt_pre

if __name__ == "__main__":
    app.run()