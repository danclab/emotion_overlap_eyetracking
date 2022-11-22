data <- make_eyetrackingr_data(df, 
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
                                         aois = c("Face","Distractor"), summarize_by='Trial')

# visualize time results
plot(response_time, predictor_column = "Emotion") + 
  theme_light() +
  coord_cartesian(ylim = c(0,1))