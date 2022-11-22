import itertools
from psychopy import visual, core, event, clock, monitors
import numpy as np
import pandas as pd
from psychopy import gui
from datetime import datetime
import random
import os
import itertools
from math import atan2, degrees

from psychopy.sound import Sound
from psychopy_tobii_infant import TobiiInfantController
from psychopy.constants import FINISHED

def run(numOfBlocks, numOfTrials):
    # Get experiment start time
    datetime_exp_start = datetime.now()

    # GUI interface
    myDlg = gui.Dlg(title="experiment")
    myDlg.addText('Subject info')
    myDlg.addField('ID:')
    myDlg.addField('Age:')
    myDlg.addField('Gender:', choices=["Female", "Male"])
    myDlg.addField('Date:',initial=datetime_exp_start.strftime('%Y.%m.%d'))
    myDlg.addField('Screens', initial=1, choices=["1", "2"])
    myDlg.addField('Eyetracker', initial=False, choices=[True, False])

    
    # show dialog and wait for OK or Cancel
    ok_data = myDlg.show() 

    # or if ok_data is not None
    if myDlg.OK: 
        id = myDlg.data[0]
        age = myDlg.data[1]
        gender = myDlg.data[2]
        date = myDlg.data[3]
        screens = myDlg.data[4]
        eyetracker = myDlg.data[5]

        print('ID: {}'.format(id))
        print('Age: {}'.format(age))
        print('Gender: {}'.format(gender))
        print('Date: {}'.format(date))
        print('Eyetracker: {}'.format(eyetracker))

    else:
        print('user cancelled')

    log_fname='overlap_{}_{}.tsv'.format(id, date)
    eye_fname='overlap_{}_{}_eyetracking.tsv'.format(id, date)
    if not os.path.exists('data'):
        os.mkdir('data')

    infant_mon = monitors.Monitor('infant_monitor', width=52, distance=80)
    infant_mon.setSizePix((1920,1200))
    infant_win = visual.Window([1920, 1200], monitor=infant_mon, screen=1, fullscr=True, color=(1,1,1))
    if screens=="2":
        exp_win = visual.Window([1920, 1200], monitor="testMonitor", units="deg", screen=0, color=(1,1,1))

    (ms_per_frame, _, _) = infant_win.getMsPerFrame()

    # show in 2 screens 
    def make_draw_mirror(draw_fun):
        def mirror_draw_fun(*args, **kwargs):
            draw_fun(win=exp_win)
            draw_fun(*args, **kwargs)
        return mirror_draw_fun
    def make_flip_mirror(flip_fun):
        def mirror_flip_fun(*args, **kwargs):
            exp_win.flip(*args, **kwargs)
            flip_fun(*args, **kwargs)
        return mirror_flip_fun
    infant_win.flip=make_flip_mirror(infant_win.flip)

    def quit():
        # Close windows
        infant_win.close()
        exp_win.close()

        # stop  eye tarcker recording
        if eyetracker:
            controller.stop_recording()
        # close the file
        if eyetracker:
            controller.close()

        data.to_csv(os.path.join('data', log_fname), sep="\t")
        core.quit()

    event.globalKeys.add(key='q', func=quit, name='shutdown')

    text = visual.TextStim(infant_win, text=" Welcome to this experiment! Connecting to eyetracker... ", color='black', pos=(0, 0))
    if screens == "2":
        text.draw = make_draw_mirror(text.draw)
    text.draw()
    infant_win.flip()

    if eyetracker:
        detected=False
        while not detected:
            try:
                # initialize TobiiInfantController to communicate with the eyetracker
                controller = TobiiInfantController(infant_win, exp_win)
                detected=True
            except:
                pass

    vidDir = "fwdvideos/"
    tex = np.array([[1, -1], [-1, 1]])
    blink_freq = 10
    state_on = False
    fps = 1000 * 1 / ms_per_frame
    state_dur = np.floor(fps / blink_freq / 2)
    change_frame = 2

    multiplier = np.min([infant_win.size[0] / 480, infant_win.size[1] / 360])
    new_size = [int(480 * multiplier), int(360 * multiplier)]
    attention_vid_fnames = [vidDir + "attentionvid1.mp4",
                            vidDir + "attentionvid2.mp4",
                            vidDir + "attentionvid3.mp4",
                            vidDir + "attentionvid4.mp4",
                            vidDir + "attentionvid5.mp4"]

    text = visual.TextStim(infant_win, text=" Loading attention videos  ", color='black', pos=(0, 0))
    if screens == "2":
        text.draw = make_draw_mirror(text.draw)
    text.draw()
    infant_win.flip()

    attention_vids = []
    for attention_vid_fname in attention_vid_fnames:
        attention_vids.append(
            visual.MovieStim3(infant_win, attention_vid_fname, flipVert=False, loop=True, size=new_size))

    videos_blocks_names = [vidDir + "mov1.mp4",
                           vidDir + "mov2.mp4",
                           vidDir + "mov3.mp4",
                           vidDir + "mov4.mp4",
                           vidDir + "mov5.mp4",
                           vidDir + "mov6.mp4",
                           vidDir + "mov7.mp4",
                           vidDir + "mov8.mp4",
                           vidDir + "mov9.mp4",
                           vidDir + "mov10.mp4",
                           vidDir + "mov11.mp4",
                           vidDir + "mov12.mp4",
                           vidDir + "mov13.mp4"]

    text = visual.TextStim(infant_win, text=" Loading inter-block videos  ", color='black', pos=(0, 0))
    if screens == "2":
        text.draw = make_draw_mirror(text.draw)
    text.draw()
    infant_win.flip()

    videos_blocks = []
    for videos_blocks_name in videos_blocks_names:
        videos_blocks.append(
            visual.MovieStim3(infant_win, videos_blocks_name, flipVert=False, loop=True, size=new_size))

    # Press key screen
    text = visual.TextStim(infant_win, text=" Press space to continue !  ", color='black', pos = (0, 0))
    if screens=="2":
        text.draw=make_draw_mirror(text.draw)
    text.draw()
    infant_win.flip()
    event.waitKeys(keyList=['space'])

    # Create empty dataframe to store trial data
    data=pd.DataFrame()

    attn_threshold_dist=.5
    attn_threshold_frames=20
    
    # # show the relative position of the subject to the eyetracker
    # # Press space to exitn
    if eyetracker:
        eyepos = visual.Circle(exp_win, radius=.5, fillColor='red', pos=(0,0))

        controller.show_status()

        # # stimuli for calibration
        CALISTIMS = [x for x in os.listdir('infant/') if '.png' in x]
        # # correct path for calibration stimuli
        CALISTIMS = ['./infant/{}'.format(x) for x in CALISTIMS]
        audio=Sound('./wawa-1.wav')
        controller.run_calibration([(-0.4, 0.4), (-0.4, -0.4), (0.0, 0.0), (0.4, 0.4), (0.4, -0.4)], CALISTIMS, audio=audio)

        # Start recording eyetracking data
        controller.start_recording(os.path.join('data', eye_fname))

    # Loop over all blocks
    status_text = visual.TextStim(exp_win, text="Block: \n, Trial: \n", color='black',
                                  pos=(0, 0.4))

    for block in range(numOfBlocks):        

        if eyetracker:
            if block>0:
                controller.stop_recording()
                controller.show_status()
                status_text.setText("Recalibrate (y/n)?")
                while True:
                    status_text.draw()
                    infant_win.flip()
                    key = event.getKeys()
                    if 'y' in key:
                        audio = Sound('./wawa-1.wav')
                        controller.run_calibration([(-0.4, 0.4), (-0.4, -0.4), (0.0, 0.0), (0.4, 0.4), (0.4, -0.4)],
                                                   CALISTIMS, audio=audio)
                        break
                    elif 'n' in key:
                        break

                controller.start_recording(os.path.join('data', eye_fname), newfile=False)
            controller.record_event('block-{}'.format(block))

        pause_video = random.choice(videos_blocks)
        status_text.setText('Press s to start block')
        pause_video.play()
        while pause_video.status != visual.FINISHED:
            gaze_pos = controller.get_current_gaze_position()
            eyepos.pos = gaze_pos
            eyepos.draw()
            pause_video.draw()
            status_text.draw()
            infant_win.flip()
            key = event.getKeys()
            if 's' in key :
                break
        pause_video.pause()

        trial_emotions = ["Anger", "Fear", "Joy", "Neutral"]
        trial_actors = ["F02", "F04", "F02", "F04"]
        possible_sides = [['L','R','L','R'], ['R','L','R','L']]
        random.shuffle(trial_emotions)
        random.shuffle(trial_actors)
        trial_sides=random.choice(possible_sides)

        # Loop over trials within this block
        for trial in range(numOfTrials):
            emotion=trial_emotions[trial]
            actor=trial_actors[trial]
            side=trial_sides[trial]

            status_text.setText("Block: {}\nTrial: {}\nCondition: {} - {} - {}".format((block+1),(trial+1),emotion, actor, side))
            status_text.draw()

            # Select random index between 0 and the length of the list
            attentionVid = random.choice(attention_vids)
            stimName = vidDir + actor + "-" + emotion
            videoStim = visual.MovieStim3(infant_win, stimName + ".mp4", flipVert=False, units='deg', size=(26.112, 20.8896))
            imageStim = visual.ImageStim(infant_win, stimName + ".png", pos=[0, 0], units='deg', size=(26.112, 20.8896))
            if side == 'R':
                gratingStim = visual.GratingStim(infant_win, tex=tex, size=(4.3, 15.4), sf=None, interpolate=False,
                                                 pos=(13.6, 0), units='deg')
            else:
                gratingStim = visual.GratingStim(infant_win, tex=tex, size=(4.3, 15.4), sf=None, interpolate=False,
                                                 pos=(-13.6, 0), units='deg')

            ###
            # PLAY ATTENTION-GRABBER
            ##
            gaze_frame_count=0
            attentionVid.play()
            while attentionVid.status != visual.FINISHED:
                if eyetracker:
                    gaze_pos=controller.get_current_gaze_position()
                    eyepos.pos = gaze_pos
                    eyepos.draw()

                    distance=np.sqrt((gaze_pos[0]**2)+(gaze_pos[1]**2))
                    if (not np.isnan(distance)) and distance<attn_threshold_dist:
                        gaze_frame_count+=1
                    else:
                        gaze_frame_count=0
                attentionVid.draw()
                text.pos = (0, -0.7)
                text.draw()
                status_text.draw()
                infant_win.flip()
                key = event.getKeys()
                if 'space' in key or gaze_frame_count>=attn_threshold_frames:
                    break
            attentionVid.pause()

            trial_clock = core.Clock()

            ###
            # PLAY FACIAL EXPRESSION VIDEO
            ##
            # Record trial start event
            if eyetracker:
                controller.record_event('trial_start')
            vid_start_time = trial_clock.getTime()
            while trial_clock.getTime()-vid_start_time<=3 and videoStim.status != FINISHED:
                status_text.draw()
                videoStim.draw()
                infant_win.flip()
                gaze_pos = controller.get_current_gaze_position()
                eyepos.pos = gaze_pos
                eyepos.draw()

            ###
            # BLINKING CHECKERBOARD
            ##
            if eyetracker:
                controller.record_event('blink')
            vid_pause_time = trial_clock.getTime()
            frameN = 0
            while trial_clock.getTime() - vid_pause_time <= 1:
                imageStim.draw()
                if state_on:
                    gratingStim.draw()
                if frameN >= change_frame:
                    state_on = not state_on
                    frameN = 0
                    change_frame = state_dur
                frameN += 1
                status_text.draw()
                infant_win.flip()
                gaze_pos = controller.get_current_gaze_position()
                eyepos.pos = gaze_pos
                eyepos.draw()

            ###
            # STATIC FACE AND CHECKERBOARD
            ##
            if eyetracker:
                controller.record_event('static')
            static_time = trial_clock.getTime()
            while trial_clock.getTime() - static_time <= 2:
                imageStim.draw()
                gratingStim.draw()
                status_text.draw()
                infant_win.flip()
                gaze_pos = controller.get_current_gaze_position()
                eyepos.pos = gaze_pos
                eyepos.draw()

            # Get trial duration
            trial_dur = trial_clock.getTime()

            # Record trial end event
            if eyetracker:
                controller.record_event('trial_stop')

            print('Trial duration= %.3f' % trial_dur)

            data=data.append({
                'subject_id': id,
                'age': age,
                'gender':gender,
                'block': block,
                'overall_trial': (block*nTrial)+trial,
                'trial': trial,
                'actor': actor,
                'emotion': emotion,
                'vid_start_time': vid_start_time,
                'vid_pause_time': vid_pause_time,
                'static_time': static_time,
                'trial_duration':trial_dur,
                'checkerboard_side':side,
                'trial_start':datetime_exp_start,
            },ignore_index=True)
            data.to_csv(os.path.join('data', log_fname), sep="\t")

    quit()


if __name__ == "__main__":
    nBlocks = 20
    nTrial  = 4
    run(nBlocks, nTrial)