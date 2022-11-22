import os
import os.path
from PIL import Image, ImageDraw

l_rect_aio=[-0.96, 0.76, -0.5, -0.76]
r_rect_aio=[0.5, 0.76, 0.96, -0.76]
face_aoi=[-0.3, 0.7, 0.3, -0.6]
out_path='/home/bonaiuto/Dropbox/joint_attention/devmobeta/aoi_frames/'
img_path='/home/bonaiuto/Dropbox/joint_attention/devmobeta/exp_frames/'
pths=os.listdir(img_path)

for pth in pths:
    files=os.listdir(os.path.join(img_path,pth))
    for file in files:
        img=Image.open(os.path.join(img_path, pth, file))
        w=img.width
        h=img.height

        face_coords_center = [face_aoi[0] * (w / 2), face_aoi[1] * (h / 2), face_aoi[2] * (w / 2), face_aoi[3] * (h / 2)]
        face_coords_top_left = [((w / 2) + face_coords_center[0], (h / 2) - face_coords_center[1]),
                                ((w / 2) + face_coords_center[2], (h / 2) - face_coords_center[3])]

        l_rect_center = [l_rect_aio[0] * (w / 2), l_rect_aio[1] * (h / 2), l_rect_aio[2] * (w / 2), l_rect_aio[3] * (h / 2)]
        l_rect_coords_top_left = [((w / 2) + l_rect_center[0], (h / 2) - l_rect_center[1]),
                                ((w / 2) + l_rect_center[2], (h / 2) - l_rect_center[3])]

        r_rect_center = [r_rect_aio[0] * (w / 2), r_rect_aio[1] * (h / 2), r_rect_aio[2] * (w / 2), r_rect_aio[3] * (h / 2)]
        r_rect_coords_top_left = [((w / 2) + r_rect_center[0], (h / 2) - r_rect_center[1]),
                                  ((w / 2) + r_rect_center[2], (h / 2) - r_rect_center[3])]

        img1 = ImageDraw.Draw(img)
        img1.rectangle(face_coords_top_left, fill=None, outline="red")
        img1.rectangle(l_rect_coords_top_left, fill=None, outline="green")
        img1.rectangle(r_rect_coords_top_left, fill=None, outline="blue")
        #img.show()

        if not os.path.exists(os.path.join(out_path, pth)):
            os.mkdir(os.path.join(out_path, pth))
        out_fname=os.path.join(out_path, pth, file)
        img.save(out_fname,'png')
        img.close()