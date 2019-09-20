echo "Enter the mode 'dev' or 'prod'"
read mode
if [ $mode == "prod" ]
then
echo "INFO => "  $mode
if [ -f "serverlessProd.yml" ]
then
echo $mode "Yml exists"

echo "INFO => Creating yaml file"
cp  "serverlessProd.yml" "serverless.yml"
echo "last command execute status " $?
if [ $? ]
then
echo "INFO => File created successfully"
echo "If you want to  deploy enter 'deploy' or to remove deployment enter 'remove'"
read status
if [ $status == "deploy" ]
then
echo "INFO => Production Enviroment for "$mode

echo "If you to deploy 'all' function or 'one' function"
read function

if [ $function == "all" ]
then
sls deploy
elif [ $function == "one" ]
then
echo "Enter the function name"
read functionName
sls deploy  -f $functionName
else
echo " Enter valid option"
fi 

elif [ $status == "remove" ]
then
echo "INFO => Removing deployment for "$mode
sls remove
else
echo "Enter valid value"
fi
echo "INFO => Completed"
echo "INFO => Deleting yml file"
rm -rf "serverless.yml"
echo "INFO => Done Over"
fi

else
echo "File not exist"
fi
elif [ $mode == "dev" ]
then
echo "INFO => "  $mode
if [ -f "serverlessDev.yml" ]
then
echo $mode "Yml exists"

echo "INFO => Creating yaml file"
cp  "serverlessDev.yml" "serverless.yml"
echo "last command execute status " $?
if [ $? ]
then
echo "INFO => File created successfully"
echo "If you want to  deploy enter 'deploy' or to remove deployment enter 'remove'"
read status
if [ $status == "deploy" ]
then
echo "INFO => Deploying Enviroment for "$mode


echo "If you to deploy 'all' function or 'one' function"
read function

if [ $function == "all" ]
then
sls deploy
elif [ $function == "one" ]
then
echo "Enter the function name"
read functionName
sls deploy  -f $functionName
else
echo " Enter valid option"
fi 


elif [ $status == "remove" ]
then
echo "INFO => Removing deployment for "$mode
sls remove
else
echo "Enter valid value"
fi
echo "INFO => Completed"
echo "INFO => Deleting yml file"
rm -rf "serverless.yml"
echo "INFO => Done Over"
fi

else
echo "File not exist"
fi
else
echo "Please enter valid mode"
fi