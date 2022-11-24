from unittest import result 
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import pandas as pd
import seaborn as sns



actor_IDs = ['F01', 'F02', 'F03', 'F04', 'F05']
emotions = ['Anger','Fear','Joy', 'Neutral']
video_path = r"C:\Users\salaviza\Projects\motion computation\adfes"
df = pd.read_csv(os.path.join(video_path, 'results.csv'), sep=";", index_col=0 )

bc_sum = []
emotionID = []
subjectID = []
  
for actor in actor_IDs:
    condition = df.loc[(df['actor_IDs'] == actor ) & (df["emotions"] == "Neutral")]
    
    for emotion in emotions:
        subjectID.append(actor)
        neutral_sum=condition['sum'].values[0]

        emotionID.append(emotion)
        condition2 = df.loc[(df['actor_IDs'] == actor ) & (df['emotions'] == emotion)]
        condition2_sum=condition2['sum'].values[0]
        sum_diff=condition2_sum - neutral_sum
        bc_sum.append(sum_diff / neutral_sum)

# Create dataframe
data = {'actor_IDs':subjectID, 'emotions':emotionID, 'bc_sum': bc_sum}
df2 = pd.DataFrame(data)

# Plot
ax1 = sns.barplot(x = 'emotions', y = 'bc_sum', hue = 'actor_IDs', data = df2)
ax1.set_title('Grouped bar plot bc_sum')
plt.show()

# Write data to file
fp = open('results_sum.csv','w')
fp.write('actor_IDs,emotions,bc_sum\n')
for i in range(len(subjectID)):
    fp.write(subjectID[i]+','+emotionID[i]+','+str(bc_sum[i])+'\n')

fp.flush()