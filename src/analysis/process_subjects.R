library(eyetrackingR)
library("ggplot2")

subjects<-c('AM','HR','MG','SA')
dates<-c('2022.09.15','2022.09.09','2022.09.15','2022.09.15')

all_data<-data.frame()
for(i in 1:length(subjects)){
  subject<-subjects[i]
  date<-dates[i]
  
  # Read eyetracking data - skip first 5 lines
  df<-read.csv(paste0('data/overlap_',subject,'_',date,'_eyetracking.tsv'),sep='\t',skip=5)
  
  # Read log file
  log_df<-read.csv(paste0('data/overlap_',subject,'_',date,'.tsv'),sep='\t')
  log_df$overall_trial<-log_df$block*4+log_df$trial
  
  # Find where the event information is (at the end of the eyetracking data file)
  # It will start from the first row that ValidityLeft is NA
  event_rows<-which(is.na(df$ValidityLeft))
  # Create a dataframe with event timings. The event name is in the second column
  # of the file, so in the column called GazePointXLeft
  event_info<-data.frame(TimeStamp=df$TimeStamp[event_rows], 
                         Event=df$GazePointXLeft[event_rows])
  # Convert the timestamp to a number
  event_info$TimeStamp<-as.numeric(event_info$TimeStamp)
  # Remove event information from eyetracking dataframe
  df<-df[which(!is.na(df$ValidityLeft)),]
  
  # Convert timestamp and GazePointXLeft columns to numbers
  df$TimeStamp<-as.numeric(df$TimeStamp)
  df$GazePointXLeft<-as.numeric(df$GazePointXLeft)
  # Set participant ID (just need some value for now)
  df$Participant<-i
  # Trackless is wherever either eye signal is invalid
  df$Trackloss <- df$ValidityLeft==0 | df$ValidityRight==0
  
  # Create trial and message columns
  df$Trial<-NA
  df$Message<-''
  
  # Get trial start and end times from event dataframe
  trial_starts<-event_info$TimeStamp[event_info$Event=='trial_start']
  trial_stops<-event_info$TimeStamp[event_info$Event=='trial_stop']
  
  # Iterate over trials
  for(trial_idx in 1:length(trial_starts)) {
    # Trial start and end time
    tstart<-trial_starts[trial_idx]
    tstop<-trial_stops[trial_idx]
    
    # Find start and stop rows from dataframe
    start_idx=which.min(abs(tstart-df$TimeStamp))
    stop_idx=which.min(abs(tstop-df$TimeStamp))
    
    # Set Message column value when trial starts and stops
    df$Message[start_idx]<-'TrialStart'
    df$Message[stop_idx]<-'TrialStop'
    
    # Set trial column
    df$Trial[start_idx:stop_idx]<-trial_idx
  }
  
  # Add blink and static events to Message column
  blinks<-event_info$TimeStamp[event_info$Event=='blink']
  statics<-event_info$TimeStamp[event_info$Event=='static']
  for(i in 1:length(blinks)) {
    blink<-blinks[i]
    idx=which.min(abs(blink-df$TimeStamp))
    df$Message[idx]<-'Blink'
  }
  for(i in 1:length(statics)) {
    static<-statics[i]
    idx=which.min(abs(static-df$TimeStamp))
    df$Message[idx]<-'Static'
  }
  
  # Remove data from in between trials
  df<-df[which(!is.na(df$Trial)),]
  
  # Set emotion and checkboard size columns from log file
  df$Emotion<-''
  df$CheckerBSide<-''
  for(i in 1:length(trial_starts)) {
    emotion<-log_df$emotion[log_df$overall_trial==(i-1)]
    side<-log_df$checkerboard_side[log_df$overall_trial==(i-1)]
    df$Emotion[df$Trial==i]<-emotion
    df$CheckerBSide[df$Trial==i]<-side
  }
  
  # Add face AOI
  face_aoi<-data.frame(Left=-0.3, Top=0.7, Right=0.3, Bottom=-0.6)
  df <- add_aoi(df, aoi_dataframe = face_aoi, 
                x_col = "GazePointX", y_col = "GazePointY", aoi_name = "Face",
                x_min_col = "Left", x_max_col = "Right", y_max_col = "Top", 
                y_min_col = "Bottom")
  table(df$Face)
  
  checkerboard_aoi<-data.frame(CheckerBSide=c('L','R'), 
                               Left=c(-0.845,0.615), 
                               Top=c(0.66,0.66), 
                               Right=c(-0.615,0.845), 
                               Bottom=c(-0.66,-0.66))
  df <- add_aoi(df, aoi_dataframe = checkerboard_aoi, 
                x_col = "GazePointX", y_col = "GazePointY", aoi_name = "Distractor",
                x_min_col = "Left", x_max_col = "Right", y_max_col = "Top", 
                y_min_col = "Bottom")
  table(df$Distractor)
  
  write.csv(df, paste0('data/overlap_',subject,'_',date,'_eyetracking_processed.csv'))
  
  all_data<-rbind(all_data, df)
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
#response_window <- subset_by_window(data, window_start_msg = "Blink", 
#                                    window_end_msg="Static", msg_col = "Message", 
#                                    rezero= FALSE, remove= TRUE)

# analyze amount of trackloss by subjects and trials
(trackloss <- trackloss_analysis(data = data))

data_clean <- clean_by_trackloss(data = data, trial_prop_thresh = .25)

trackloss_clean <- trackloss_analysis(data = data_clean)

(trackloss_clean_subjects <- unique(trackloss_clean[, c('Participant','TracklossForParticipant')]))

# aggregate across trials within subjects in time analysis
response_time <- make_time_sequence_data(data_clean, time_bin_size = 200, 
                                         predictor_columns = c('Emotion'),
                                         aois = c("Face","Distractor"), summarize_by='Participant')

# visualize time results
plot(response_time, predictor_column = "Emotion") + 
  theme_light() +
  coord_cartesian(ylim = c(0,1))