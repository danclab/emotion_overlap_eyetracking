import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
#from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
import matplotlib.image as mpimg

subject='SA'
#subject='MG'
#date='2022.07.18'
date='2022.09.15'
data_path='/home/bonaiuto/Dropbox/joint_attention/devmobeta/data/'
out_path=os.path.join('/home/bonaiuto/Dropbox/joint_attention/devmobeta/output/',subject)
if not os.path.exists(out_path):
    os.mkdir(out_path)

eye_data=pd.read_csv(os.path.join(data_path, 'overlap_{}_{}_eyetracking_processed.csv'.format(subject, date)),header=0)
log_data=pd.read_csv(os.path.join(data_path, 'overlap_{}_{}.tsv'.format(subject, date)),sep='\t')
log_data['overall_trial']=log_data['block']*4+log_data['trial']+1
trials=np.unique(eye_data['Trial'])

condition_maps={
    ''
}

for trial in trials:
    trial_data=eye_data.loc[eye_data['Trial'] == trial]
    trial_log_data=log_data.loc[log_data['overall_trial']==trial]

    actor=trial_log_data['actor'].iloc[0]
    emotion=trial_log_data['emotion'].iloc[0]
    side=trial_log_data['checkerboard_side'].iloc[0]

    condition='{}'

    trial_data=trial_data.reset_index()

    base_img_fname = os.path.join('/home/bonaiuto/Dropbox/joint_attention/devmobeta/aoi_frames','{}_{}_{}'.format(actor,emotion,side),
                     'actor_{}_emotion_{}_side_{}_092.png'.format(actor,emotion,side))

    base_img = mpimg.imread(base_img_fname)
    w = base_img.shape[1]
    h = base_img.shape[0]

    mask=np.zeros((h,w))

    x_data=np.array(trial_data['GazePointX'])
    y_data = np.array(trial_data['GazePointY'])
    for x,y in zip(x_data, y_data):
        x_pix_center = x * (w / 2)
        x_pix_top_left = (w / 2) + x_pix_center
        y_pix_center = y * (h / 2)
        y_pix_top_left = (h / 2) - y_pix_center
        frame_mask = np.zeros((h, w))
        if not np.isnan(x_pix_top_left) and not np.isnan(y_pix_top_left):
            if int(y_pix_top_left)<frame_mask.shape[0] and int(x_pix_top_left)<=frame_mask.shape[1]:
                frame_mask[int(y_pix_top_left),int(x_pix_top_left)]=1
                #frame_mask=10*gaussian_filter(frame_mask, sigma=50)
                mask=mask+frame_mask
    mask = gaussian_filter(mask, sigma=50)
    mask[mask<0.0001]=float('NaN')
    plt.figure()
    plt.imshow(base_img)
    plt.imshow(mask, alpha=.3)
    #plt.show()
    plt.savefig(os.path.join(out_path,'%s_%s_trial_%03d.png' % (subject, date, trial)))
    plt.close()

    # for index, row in trial_data.iterrows():
    #     base_img = Image.open(base_img_fname)
    #     w = base_img.width
    #     h = base_img.height
    #
    #     x=row['GazePointX']
    #     y=row['GazePointY']
    #     x_pix_center=x*(w/2)
    #     x_pix_top_left = (w/2)+x_pix_center
    #     y_pix_center=y*(h/2)
    #     y_pix_top_left = (h / 2) - y_pix_center
    #
    #     img1 = ImageDraw.Draw(base_img)
    #     img1.ellipse([(x_pix_top_left-10), (y_pix_top_left-10), (x_pix_top_left+10), (y_pix_top_left+10)], fill="red", outline="red")
    #
    #     out_fname = os.path.join('/home/bonaiuto/Dropbox/joint_attention/devmobeta/output/trial_%03d_frame_%03d.png' % (trial,index))
    #     base_img.save(out_fname, 'png')
    #     base_img.close()