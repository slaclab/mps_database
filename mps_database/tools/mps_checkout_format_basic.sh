source /usr/local/lcls/package/anaconda/envs/python3.7env/bin/activate;
export PYTHONPATH=/usr/local/lcls/tools/python/toolbox;

ls -v $1* > fileList.txt


for file in $(cat fileList.txt)
do
    tempFile=${file#*App}
    dictFile=App$tempFile
    python mps_checkout_format_basic.py -SrcFileLoc=$1 -SrcFileName=$dictFile -LogFileLoc=$2 -LogFileName=$3
done

rm fileList.txt
