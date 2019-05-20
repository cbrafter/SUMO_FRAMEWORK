# start new file and write header to sorted_$filename
head -n 1 $1 > sorted_$1
# write everything after the header to tempdata.csv
tail -n +2 $1 > tempdata.csv
# split the data into smaller chunks of 500K lines and save to tempfileNN
# (-d) ends each split with a number rather than a letter
split -d -l 500000 tempdata.csv tempfile
# remove tempdata.csv file now that it is split up
rm tempdata.csv
# for each tempfile
for file in $(ls tempfile*); do
    # sort by the second column (k2) and then the first column (k1)
    # (-t ,) indicates data is sorted by commas
    # -n sorts data as numeric values not strings
	sort -t , -n -k2 -k1 $file > sorted_$file
	rm $file  # remove old unsorted tempfile
done
# merge sort (-m) the sorted tempfiles based on second then first column sorted_$filename
sort -m -t , -n -k2 -k1 sorted_tempfile* >> sorted_$1  
rm sorted_tempfile*  # remove tempfile
# rm sorted_