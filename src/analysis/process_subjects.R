library(eyetrackingR)
library("ggplot2")
library('lme4')
library('car')

subjects<-c('FM','FMS','LZ','RA')
dates<-c('2022.11.17','2022.11.17','2022.10.17','2022.11.15')

all_data<-data.frame()
for(sub_idx in 1:length(subjects)){
  subject<-subjects[sub_idx]
  date<-dates[sub_idx]
  
  # Read eyetracking data - skip first 5 lines
  df<-read.csv(paste0('../../data/overlap_',subject,'_',date,'_eyetracking.tsv'),sep='\t',skip=5)
  df<-df[df$TimeStamp!='TimeStamp' & df$TimeStamp!='Session Start',]
  df$ValidityLeft<-as.numeric(df$ValidityLeft)
  df$ValidityRight<-as.numeric(df$ValidityRight)
  
  # Read log file
  log_df<-read.csv(paste0('../../data/overlap_',subject,'_',date,'.tsv'),sep='\t')
  log_df$overall_trial<-log_df$block*4+log_df$trial
  
  
  blk_start<-1
  blk_ends<-which(df$TimeStamp=='Session End')
  overall_trial<-1
  
  subj_df<-data.frame()
  
  for(blk_idx in 1:length(blk_ends)) {
    block_df<-df[blk_start:blk_ends[blk_idx]-1,]
    
    # Find where the event information is (at the end of the eyetracking data file)
    # It will start from the first row that ValidityLeft is NA
    event_rows<-which(is.na(block_df$ValidityLeft))
    # Create a dataframe with event timings. The event name is in the second column
    # of the file, so in the column called GazePointXLeft
    event_info<-data.frame(TimeStamp=block_df$TimeStamp[event_rows], 
                           Event=block_df$GazePointXLeft[event_rows])
    # Convert the timestamp to a number
    event_info$TimeStamp<-as.numeric(event_info$TimeStamp)
    
    # Remove event information from eyetracking dataframe
    block_df<-block_df[which(!is.na(block_df$ValidityLeft)),]
    
    # Convert timestamp and GazePointXLeft columns to numbers
    block_df$TimeStamp<-as.numeric(block_df$TimeStamp)
    block_df$GazePointX<-as.numeric(block_df$GazePointX)
    block_df$GazePointY<-as.numeric(block_df$GazePointY)
    
    # Set participant ID (just need some value for now)
    block_df$Participant<-sub_idx
    # Trackless is wherever either eye signal is invalid
    block_df$Trackloss <- block_df$ValidityLeft==0 & block_df$ValidityRight==0
    
    # Create trial and message columns
    block_df$Trial<-NA
    block_df$Message<-''
    
    # Get trial start and end times from event dataframe
    trial_starts<-event_info$TimeStamp[event_info$Event=='trial_start']
    trial_stops<-event_info$TimeStamp[event_info$Event=='trial_stop']
    
    # Iterate over trials
    for(trial_idx in 1:length(trial_starts)) {
      # Trial start and end time
      tstart<-trial_starts[trial_idx]
      tstop<-trial_stops[trial_idx]
      
      # Find start and stop rows from dataframe
      start_idx=which.min(abs(tstart-block_df$TimeStamp))
      stop_idx=which.min(abs(tstop-block_df$TimeStamp))
      
      # Set Message column value when trial starts and stops
      block_df$Message[start_idx]<-'TrialStart'
      block_df$Message[stop_idx]<-'TrialStop'
      
      # Set trial column
      block_df$Trial[start_idx:stop_idx]<-overall_trial
      overall_trial<-overall_trial+1
    }
    
    # Add blink and static events to Message column
    blinks<-event_info$TimeStamp[event_info$Event=='blink']
    statics<-event_info$TimeStamp[event_info$Event=='static']
    for(i in 1:length(blinks)) {
      blink<-blinks[i]
      idx=which.min(abs(blink-block_df$TimeStamp))
      block_df$Message[idx]<-'Blink'
    }
    for(i in 1:length(statics)) {
      static<-statics[i]
      idx=which.min(abs(static-block_df$TimeStamp))
      block_df$Message[idx]<-'Static'
    }
    
    # Remove data from in between trials
    block_df<-block_df[which(!is.na(block_df$Trial)),]
    
    # Set emotion and checkboard size columns from log file
    block_df$Emotion<-''
    block_df$CheckerBSide<-''
    for(i in 1:length(trial_starts)) {
      emotion<-log_df$emotion[log_df$overall_trial==(i-1)]
      side<-log_df$checkerboard_side[log_df$overall_trial==(i-1)]
      block_df$Emotion[block_df$Trial==i]<-emotion
      block_df$CheckerBSide[block_df$Trial==i]<-side
    }
    
    # Add face AOI
    face_aoi<-data.frame(Left=-0.3, Top=0.7, Right=0.3, Bottom=-0.6)
    block_df <- add_aoi(block_df, aoi_dataframe = face_aoi, 
                  x_col = "GazePointX", y_col = "GazePointY", aoi_name = "Face",
                  x_min_col = "Left", x_max_col = "Right", y_max_col = "Top", 
                  y_min_col = "Bottom")
    table(block_df$Face)
    
    checkerboard_aoi<-data.frame(CheckerBSide=c('L','R'), 
                                 Left=c(-0.96,0.5), 
                                 Top=c(0.76,0.76), 
                                 Right=c(-0.5,0.96), 
                                 Bottom=c(-0.76,-0.76))
    block_df <- add_aoi(block_df, aoi_dataframe = checkerboard_aoi, 
                  x_col = "GazePointX", y_col = "GazePointY", aoi_name = "Distractor",
                  x_min_col = "Left", x_max_col = "Right", y_max_col = "Top", 
                  y_min_col = "Bottom")
    table(block_df$Distractor)
    
    subj_df<-rbind(subj_df, block_df)
    
    blk_start<-blk_ends[blk_idx]+1
  }
  write.csv(subj_df, paste0('../../data/overlap_',subject,'_',date,'_eyetracking_processed.csv'))
  
  all_data<-rbind(all_data, subj_df)
}

data <- make_eyetrackingr_data(all_data, 
                               participant_column = "Participant",
                               trial_column = "Trial",
                               time_column = "TimeStamp",
                               trackloss_column = "Trackloss",
                               aoi_columns = c('Face','Distractor'),
                               treat_non_aoi_looks_as_missing = TRUE)

data <- subset_by_window(data, window_start_msg = "TrialStart", 
                         window_end_msg="TrialStop", msg_col = "Message", 
                         rezero= TRUE, remove=TRUE)

response_window <- subset_by_window(data, window_start_time = 2500, 
                                    window_end_time = 5500, rezero= FALSE, 
                                    remove= TRUE)
#response_window <- subset_by_window(data, window_start_msg = "Blink", 
#                                    window_end_msg="Static", msg_col = "Message", 
#                                    rezero= FALSE, remove= TRUE)

# analyze amount of trackloss by subjects and trials
(trackloss <- trackloss_analysis(data = response_window))

response_window_clean <- clean_by_trackloss(data = response_window, trial_prop_thresh = .25)

trackloss_clean <- trackloss_analysis(data = response_window_clean)

(trackloss_clean_subjects <- unique(trackloss_clean[, c('Participant','TracklossForParticipant')]))

mean(1 - trackloss_clean_subjects$TracklossForParticipant)
sd(1- trackloss_clean_subjects$TracklossForParticipant)

(final_summary <- describe_data(response_window_clean, 'Face', 'Participant'))

# aggregate across trials within subjects in time analysis
response_time <- make_time_sequence_data(data_clean, time_bin_size = 100, 
                                         predictor_columns = c('Emotion'),
                                         aois = c("Face","Distractor"), summarize_by='Participant')

# visualize time results
plot(response_time, predictor_column = "Emotion") + 
  theme_light() +
  coord_cartesian(ylim = c(0,1))






response_window <- subset_by_window(data, window_start_time = 2500, 
                                    window_end_time = 5500, rezero= FALSE, 
                                    remove= TRUE)


(trackloss <- trackloss_analysis(data = response_window))

response_window_clean <- clean_by_trackloss(data = response_window, trial_prop_thresh = .25)

trackloss_clean <- trackloss_analysis(data = response_window_clean)

(trackloss_clean_subjects <- unique(trackloss_clean[, c('Participant','TracklossForParticipant')]))

mean(1 - trackloss_clean_subjects$TracklossForParticipant)
sd(1- trackloss_clean_subjects$TracklossForParticipant)

(final_summary <- describe_data(response_window_clean, 'Face', 'Participant'))


onsets <- make_onset_data(response_window_clean, onset_time = 2500, 
                          fixation_window_length = 100, target_aoi='Distractor')
# participants' ability to orient to the trial target overall:
plot(onsets) + theme(legend.text=element_text(size=5))

plot(onsets, predictor_columns = "Emotion") + theme(legend.text=element_text(size=6))

onset_switches <- make_switch_data(onsets, predictor_columns = "Emotion")

# visualize subject's switch times
plot(onset_switches, predictor_columns = c("Emotion"))

# build model:
model_switches <- lmer(FirstSwitch ~ Emotion + 
                         (1 | Trial) + (1 | Participant), data=onset_switches, REML=FALSE)
# cleanly show important parts of model (see `summary()` for more)
broom::tidy(model_switches, effects="fixed")
Anova(model_switches)