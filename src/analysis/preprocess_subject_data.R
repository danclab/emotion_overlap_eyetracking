library("eyetrackingR")
# library("ggplot2")
# library("Matrix")
# library("lme4")
# library("car")
# library("emmeans")
# library("pairwiseComparisons")
# #library("ggsignif")
# library("pairwiseComparisons")

data_dir<-'/home/bonaiuto/Dropbox/Projects/inProgress/dev_mobeta/emotion_overlap_eyetracking/data/'


# List all directories (not recursively)
all_dirs <- list.dirs(data_dir, full.names = TRUE, recursive = FALSE)

# Filter to only include directories that start with 'sub-'
sub_dirs <- all_dirs[grepl("sub-", basename(all_dirs))]

# Iterate through each 'sub-' directory and find 'ses-01' directories
for(sub_dir in sub_dirs) {
  subject<-basename(sub_dir)
  print(subject)
  
  # List all directories in the current 'sub-' directory
  dir_content <- list.dirs(sub_dir, full.names = TRUE, recursive = FALSE)
  
  # Filter to only include directories that start with 'ses-01'
  ses_dirs <- dir_content[grepl("ses-", basename(dir_content))]
  
  for(ses_dir in ses_dirs) {
    session<-basename(ses_dir)
    print(session)
    
    eyetracking_dir = paste0(ses_dir,'/eyetracking')
    dir_content <- list.files(eyetracking_dir, full.names = FALSE, recursive = FALSE)
    eyetracking_fname <- dir_content[grepl("overlap", dir_content) & grepl("eyetracking.tsv", dir_content)]
    log_fname <- dir_content[grepl("overlap", dir_content) & !grepl("eyetracking.tsv", dir_content)]
    
    # Read eyetracking data - skip first 5 lines
    print(paste0(eyetracking_dir, '/', eyetracking_fname))
    df<-read.csv(paste0(eyetracking_dir, '/', eyetracking_fname),sep='\t',skip=5)
    df<-df[df$TimeStamp!='TimeStamp' & df$TimeStamp!='Session Start',]
    df$ValidityLeft<-as.numeric(df$ValidityLeft)
    df$ValidityRight<-as.numeric(df$ValidityRight)
    
    # Read log file
    print(paste0(eyetracking_dir, '/', log_fname))
    log_df<-read.csv(paste0(eyetracking_dir, '/', log_fname),sep='\t')
    log_df$overall_trial<-log_df$block*4+log_df$trial
    
    blk_start<-1
    blk_ends<-which(df$TimeStamp=='Session End')
    
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
      block_df$Participant<-subject
      # Trackless is wherever either eye signal is invalid
      block_df$Trackloss <- block_df$ValidityLeft==0 & block_df$ValidityRight==0
      
      # Create trial and message columns
      block_df$Trial<-NA
      block_df$Message<-''
      
      # Get trial start and end times from event dataframe
      trial_starts<-event_info$TimeStamp[event_info$Event=='trial_start']
      trial_stops<-event_info$TimeStamp[event_info$Event=='trial_stop']
      if(length(trial_stops)<length(trial_starts)) {
        trial_starts<-trial_starts[1:length(trial_starts)-1]
      }
      if(length(trial_starts)>0) {
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
          block_df$Trial[start_idx:stop_idx]<-trial_idx
        }
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
      if(length(trial_starts)>0) {
        block_df$Emotion<-''
        block_df$CheckerBSide<-''
        for(i in 1:length(trial_starts)) {
          emotion<-log_df$emotion[log_df$overall_trial==((blk_idx-1)*4+(i-1))]
          side<-log_df$checkerboard_side[log_df$overall_trial==((blk_idx-1)*4+(i-1))]
          block_df$Emotion[block_df$Trial==i]<-emotion
          block_df$CheckerBSide[block_df$Trial==i]<-side
        }
        block_df$Trial<-(blk_idx-1)*4+block_df$Trial
      
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
      }
      
      blk_start<-blk_ends[blk_idx]+1
    }
    write.csv(subj_df, paste0(eyetracking_dir, '/', subject,'_',session,'_eyetracking_processed.csv'))
  }
}
