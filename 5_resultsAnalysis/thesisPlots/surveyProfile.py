#!/usr/bin/python3.6
import pandas as pd
import pandas_profiling
df = pd.read_csv('SurveyData_clean.csv')
prof = df.profile_report()
prof.to_file('survey_profile.html')
