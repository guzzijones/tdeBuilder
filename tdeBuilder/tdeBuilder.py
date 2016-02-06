from tableausdk import Types as tde
from tableausdk import Extract as tdeEx
from tableausdk import Server as tdeS
from tableausdk import Exceptions as tdeE
import sys,getopt
import csv
import time
import datetime
import locale
import json
import os
import pdb    
import glob
import base64
import math
import re
import pyodbc            
class parameter(object):

    def __init__(self,inName,inDefault,setValue=""):
        self.name=inName;
        self.default=inDefault;
        self.setValue=setValue;
        if self.setValue=="":
            self.endValue=self.default
        else:
            self.endValue=self.setValue
    def getValue(self):
        return self.endValue
    def getName(self):
        return self.name

    @classmethod
    def fromjson(cls,inDict,inSetValue=""):
        name= inDict.keys()[0]
        default=inDict[name]["default"]
        setValue=inSetValue
        return cls(name,default,setValue)

class configValue(object):
    def __init__(self,stringIn,listParams):
        self.value=stringIn
        for param in listParams:
            reg= re.compile("\$\("+param.name+"\)")
            self.value= reg.sub(param.getValue(),self.value)
    def getValue(self):
        return self.value;

def encodeWordOrg(key, clear):
    enc = []
    for i in range(len(clear)):
        key_c = key[i % len(key)]
        enc_c = chr((ord(clear[i]) + ord(key_c)) % 256)
        enc.append(enc_c)
    return base64.urlsafe_b64encode("".join(enc))

def decodeWordOrg(key, enc):
    dec = []
    enc = base64.urlsafe_b64decode(enc)
    for i in range(len(enc)):
        key_c = key[i % len(key)]
        dec_c = chr((256 + ord(enc[i]) - ord(key_c)) % 256)
        dec.append(dec_c)
    return "".join(dec)

def encodeWord(clear):
    return base64.b64encode(clear)
def decodeWord(mixed):
    return base64.b64decode(mixed)

class parseInOut:
    def __init__(self,argv):
        self.encodePassword=False
        self.IFound=False
        self.PFound=False
        self.DFound=False
        self.ParamFlagValues=[]
        self.params=False
        self.dictParams={}
        try:
            opts, args = getopt.getopt(argv,"hi:p:D:",["ifile=","passwordEncode=","define"]) #: means it will  be followed by a value
        except getopt.GetoptError:
            print 'test.py -i <inputfile>  -D <param>=<value>'
            print 'test.py -p <pass>'
            sys.exit(2)
        for opt, arg in opts:
            if opt == '-h':
                print 'test.py -i <inputfile> '
                sys.exit()
            elif opt in ("-i", "--ifile"):
                self.inputfile = arg
                self.IFound=True
            elif opt in ("-p","--passwordEncode"):
                self.encodePassword=True
                self.password=arg
                self.PFound=True
            elif opt in ("-D","--define"):
                self.DFound=True
                nameValue=arg.split("=")
                self.dictParams[nameValue[0]]=nameValue[1]
            else:
                raise ValueError("Argument does not exist")                
        if self.PFound==True and self.IFound==True: # cannot have -p and -i
            raise ValueError("Cannot use -i and -p")

class source_info(object):
    ENCODINGS=[
           "utf-8",
           "ascii",
           "latin_1"
            ]
    def __init__(self,jsonIn):
        self.totalRows=0
        #default to utf-8 which is based with first 127 chars equal to ascii.  This should work for most files
        self.encodeing="utf-8"
        if "encoding" in jsonIn.keys():
            if jsonIn["encoding"] in source_info.ENCODINGS:
                self.encoding=jsonIn["encoding"];
    def setTotalRows(self):
        pass
    def getPercent(self,currentRow):
        pct=currentRow/float(self.totalRows)*100
        return pct
         # should return percent done
    def setColumnIndex(self,tdeSettings):
        pass
    def yieldRowsBase(self):
        pass # should yield a list of columns

class odbc_info(source_info):
    def __init__(self,jsonIn,parms):
        source_info.__init__(self,jsonIn)
        if "dsn" in jsonIn.keys():
            self.dsn=configValue(jsonIn["dsn"],parms).getValue()
            self.uid=configValue(jsonIn["uid"],parms).getValue()
            self.password=configValue(jsonIn["password"],parms).getValue()
            self.conn=pyodbc.connect('DSN=%s;UID=%s;PWD=%s'%(self.dsn,self.user,self.password),readonly=True,unicode_results=True)
        else:
            self.server=configValue(jsonIn["server"],parms).getValue()
            
            self.user=configValue(jsonIn["uid"],parms).getValue()
            self.password=configValue(jsonIn["password"],parms).getValue()
            self.driver=configValue(jsonIn["driver"],parms).getValue()
            print "driver:",self.driver
            self.port=configValue(jsonIn["port"],parms).getValue()
            self.database=configValue(jsonIn["database"],parms).getValue()
            conString="DRIVER={%s};SERVER=%s,%s;DATABASE=%s;UID=%s;PWD=%s"%(self.driver,self.server,self.port,self.database,self.user,self.password)
            print "con:",conString
            self.conn=pyodbc.connect(conString,readonly=True,unicode_results=True)
            
        self.sql=configValue(jsonIn["sql"],parms).getValue()
        self.cursor=self.conn.cursor()
        self.setTotalRows()
        self.totalRows=self.setTotalRows() 
                   
    def yieldRowsBase(self):
        self.cursor.execute(self.sql)
        for row in self.cursor.execute(self.sql):
            newRow=[]
            for item in row:
                if isinstance(item,unicode):
                    newRow.append(item.encode('utf-8'))
                else:
                    newRow.append(item)
            yield newRow 

    def setTotalRows(self):
        self.cursor.execute(self.sql)
        count=0
        for row in self.cursor.execute(self.sql):
            count+=1
        return count

    def setColumnIndex(self,tdeSettingsIn):
        self.cursor.execute(self.sql)
        listColumnNames=[]

        for aTuple in self.cursor.description:
            listColumnNames.append(aTuple[0])

        columnIndex={}
        for columnName,foo in tdeSettingsIn.columns.items():
            i=0
            for column in listColumnNames:
                if columnName==column:
                    columnIndex[columnName]=i
                    break
                i+=1
        return columnIndex
 
 
class file_info(source_info):
    COLUMNHEADERS={
    'HEADERS':"column_headers",
    'STANDARD':"standard"
    }
    INPUT_TYPES={
    'STARNAME':"starname",
    'FILENAME':"filename"
    }
    
    def __init__(self,jsonIn,parameters):
        source_info.__init__(self,jsonIn)
        # Define type maps
        self.input_type=""
        self.input_filenames=[]
        self.delimiter=''
        self.column_headers=""
        self.setInputType(configValue(jsonIn["input_type"],parameters).getValue())
        self.setColumnHeader(configValue(jsonIn["column_headers"],parameters).getValue())
        self.setDelimiter(configValue(jsonIn["delimiter"],parameters).getValue())
        self.setInputFileName(configValue(jsonIn["input_file_name"],parameters).getValue())
        self.totalRows=self.setTotalRows() 
        print "Totalrows:",self.totalRows
        

    def setInputFileName(self,stringIn):
        if len(glob.glob(stringIn)) > 0:
            self.input_filenames=glob.glob(stringIn)
        else:
            raise ValueError('file does not exist: ' + stringIn)

    def setTotalRows(self):
        totalRows=0
        for i in self.input_filenames:
            with open(i,'rb') as myfile:
                rowCount=sum(1 for row in myfile) 
                if self.column_headers==file_info.COLUMNHEADERS["HEADERS"]:
                    rowCount-=1 
                totalRows+=rowCount
        return totalRows

    def setDelimiter(self,stringIn):
        
        if stringIn=="\t":
            self.delimiter="\t"
        elif stringIn==",":
            self.delimiter=","
        elif stringIn==";":
            self.delimiter=";"
        else:
            raise ValueError('file_info - delimiter is not valid type of tab, comma, or semicolon')

    def setColumnIndex(self,tdeSettingsIn):
        columnIndex={}
        with open(tdeSettingsIn.inputInfo.fileInformation.input_filenames[0]) as file:
            myreader=csv.reader(file,delimiter=tdeSettingsIn.inputInfo.fileInformation.delimiter)
            row=myreader.next() #get first row which is the header
            if tdeSettingsIn.inputInfo.fileInformation.column_headers==file_info.COLUMNHEADERS["HEADERS"]:
                for columnName,foo in tdeSettingsIn.columns.items():
                    i=0
                    for column in row:
                        if columnName==column:
                            columnIndex[columnName]=i
                            break
                        i+=1
            else :
                i=0
                for column in tdeSettingsIn.columns:
                    columnIndex[column]=configValue(i,self.parameters).getValue()
                    i+=1
        return columnIndex

    def setColumnHeader(self,stringIn):
        if stringIn not in file_info.COLUMNHEADERS.values():
            raise ValueError ('file_info - column_headers is not valid of : ' + str(self.COLUMNHEADERS))
        else:
            self.column_headers=stringIn
            
    def setInputType(self,stringIn):
        if stringIn not in file_info.INPUT_TYPES.values():
            raise ValueError('file_info - input_type is not valid of: ' + str(self.INPUT_TYPES))
        else:
            self.input_type=stringIn

    def yieldRowsBase(self):
        for i in self.input_filenames:
            with open(i,'rb') as myfile:
                myreader=None
                myreader=csv.reader(myfile, delimiter=self.delimiter, quotechar='"')
                if self.column_headers==file_info.COLUMNHEADERS["HEADERS"]:
                    # skip the header row
                    next(myreader,None)
                    #for each row in the connection data
                for myReaderRow in myreader:
                    yield myReaderRow    

class inputConfig(object):
    
    TYPES={
    'TYPESQL':"sql",
    'TYPEFILE':"file"
    }
    def __init__(self,jsonIn,paramsIn):
        self.params=paramsIn
        self.type=""
        self.setType(jsonIn)
        #here we would branch if type=SQL
        if "file_info" in jsonIn.keys():
            self.fileInformation=file_info(jsonIn["file_info"],paramsIn)
        else:
            self.fileInformation=odbc_info(jsonIn["sql_info"],paramsIn)
    def setType(self,jsonIn):
        myType=configValue(jsonIn["type"],self.params).getValue()
        if myType not in self.TYPES.values():
            raise ValueError('Data Type does not exist')
        else:
            if myType=="sql":
                if not jsonIn["sql_info"]:
                    raise ValueError("sql_info key is not present")
            if myType=="file":
                if not jsonIn["file_info"]:
                    raise ValueError("file_info key is not present")
            self.type=myType
        
           
        
class tdeSettings(object):
    schemaIniTypeMap = { 
            'Bit' :     tde.Type.BOOLEAN,
            'Byte':     tde.Type.INTEGER,
            'Short':    tde.Type.INTEGER,
            'Long':     tde.Type.INTEGER,
            'Integer':  tde.Type.INTEGER,
            'Single':   tde.Type.DOUBLE,
            'Double':   tde.Type.DOUBLE,
            'Date':     tde.Type.DATE,
            'DateTime': tde.Type.DATETIME,
            'Text':     tde.Type.UNICODE_STRING,
            'Memo':     tde.Type.UNICODE_STRING 
        }
    def __init__(self,inDict,parmFlags):
        self.parameters=[]
        if "parameters" in inDict.keys():
            parametersDict=inDict["parameters"]
            for key in parametersDict.keys():
                if key in parmFlags.keys():
                    tmpParam=parameter(key,parametersDict[key]["default"],parmFlags[key]) #laster arugment is param from command line: Name, default, value
                else:
                    tmpParam=parameter(key,parametersDict[key]["default"],"") #laster arugment is param from command line: Name, default, value

                self.parameters.append(tmpParam)
        self.tde_file=configValue(inDict["tde_filename"],self.parameters).getValue()
        
        self.columnIndex={} #columns and their indexes
        self.serverUpload=False
        if "server_upload" in inDict.keys():
            self.server_address=configValue(inDict["server_upload"]["server_address"],self.parameters).getValue()
            self.server_login=configValue(inDict["server_upload"]["server_login"],self.parameters).getValue()
            self.server_password=inDict["server_upload"]["server_password_encoded"] 
            self.serverUpload=True

        self.inputInfo=inputConfig(inDict["input"],self.parameters)
        self.setColumns(inDict["columns"])
        
            

    @classmethod
    def fromfilename(cls,name,listparams):
        with open(name,'r') as myfile:
            jsonString=myfile.read()
            try:
                jsonResult=json.loads(jsonString,strict=False)
            except ValueError , e:
                print e
                raise
            return cls(jsonResult,listparams)
    #to use this as an alternate constructor
    #c = tdeSettings.fromfilename('filename.json')    
        
    def setColumns(self,columnsJson):
        #raise exception if column type does not match schemainittypemap
         
        for key,value in columnsJson.items():
            if value not in tdeSettings.schemaIniTypeMap:
                raise ValueError('Data Type does not exist')
        self.columns=columnsJson
        #set column index dict
        self.columnIndex=self.inputInfo.fileInformation.setColumnIndex(self)
        if len(self.columnIndex)==0:
            raise ValueError("Columns Object does refer to any columns in the input data")

                   
    def writeJsonFile(self):
        return json.dumps(self,default=lambda o : o.__dict__,sort_keys=True, indent=4)
            
        
            

class builder(object):
    
    def __init__(self,settingsIn):
        self.tde_settings_ins=settingsIn
        self.fieldSetterMap = {
        tde.Type.BOOLEAN:        lambda row, colNo, value: row.setBoolean( colNo, value.lower() == "true" ),
        tde.Type.INTEGER:        lambda row, colNo, value: row.setInteger( colNo, int(''.join(c for c in value if c.isdigit() or c=='.')) ),
        tde.Type.DOUBLE:         lambda row, colNo, value: row.setDouble( colNo, float(''.join(c for c in value if c.isdigit() or c=='.')) ),
        tde.Type.UNICODE_STRING: lambda row, colNo, value: row.setString( colNo, value ),
        tde.Type.CHAR_STRING:    lambda row, colNo, value: row.setCharString( colNo, value ),
        tde.Type.DATE:           lambda row, colNo, value: self.setDate(row, colNo, value),
        tde.Type.DATETIME:       lambda row, colNo, value: self.setDateTime( row, colNo, value )
        }
    
    def setDate(self,row, colNo, value) :
        if len(value)==10:
            d = datetime.datetime.strptime(value.replace("/","-"), "%Y-%m-%d")
        elif len(value)==8:
            d = datetime.datetime.strptime(value, "%Y%m%d")
        else:
            raise ValueError("Date is not a standard format")
        row.setDate( colNo, d.year, d.month, d.day )
    
    def setDateTime(self,row, colNo, value) :
        if( value.find(".") != -1) :
                d = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
        else :
                d = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        row.setDateTime( colNo, d.year, d.month, d.day, d.hour, d.minute, d.second, d.microsecond/100 )
    
    def build(self):
        # Set filename
        tdefileName = self.tde_settings_ins.tde_file;
        if os.path.isfile(tdefileName):
            os.remove(tdefileName)
        #set the extract object instance
        tdefile = tdeEx.Extract(tdefileName)
        # create the column schema
        tableDef = tdeEx.TableDefinition()
        columnsListedInOrder=[]
        outputColIndex={}
        outputColNumber=0
        for columnName,index in sorted(self.tde_settings_ins.columnIndex.items(),key=lambda x:x[1]):
            BasicDataType=self.tde_settings_ins.columns[columnName]
            tableDef.addColumn( columnName, tdeSettings.schemaIniTypeMap[BasicDataType] )
            outputColIndex[columnName]=outputColNumber
            outputColNumber+=1
        #add the column schema to the ojbect instance of EXTRACT
        table=tdefile.addTable("Extract",tableDef)
        rowNo=0

        rowsIterator=self.tde_settings_ins.inputInfo.fileInformation.yieldRowsBase()
        printedBool=False
        startTime=datetime.datetime.now()
        print "Build start time:",datetime.datetime.strftime(startTime,'%Y-%m-%d %H:%M:%S')
        prevPct=-1
        for myReaderRow in  rowsIterator:
            putRow=tdeEx.Row(tableDef)
            for columnName,index in self.tde_settings_ins.columnIndex.items():
                #if not column headers need to change this to index of the column
                if( tdeSettings.schemaIniTypeMap[self.tde_settings_ins.columns[columnName]]!= tde.Type.UNICODE_STRING and myReaderRow[index] == "" ):
                    putRow.setNull( outputColIndex[columnName])
                else :
                    try:
                        valueDecoded=myReaderRow[index].decode(self.tde_settings_ins.inputInfo.fileInformation.encodeing)
                        self.fieldSetterMap[tdeSettings.schemaIniTypeMap[self.tde_settings_ins.columns[columnName]]](putRow, outputColIndex[columnName], valueDecoded);
                    except:
                        print "column name", columnName, "contians invalid data"
                        print "value: ",myReaderRow[index] 
                        print sys.exc_info()[0]
                        raise
            table.insert(putRow)
            # Output progress line
            #only print percent one time when we hit that percent
            rowNo += 1
            pct=math.floor(self.tde_settings_ins.inputInfo.fileInformation.getPercent(rowNo))
#            print "row:",rowNo
#            print "pct:",pct
#            print "value: ",pct %2
            if pct % 2 ==0 :
                if printedBool==False or prevPct!=pct:
                    print "Percent:",round(pct,0),"%, row:",rowNo
                    printedBool=True
                    prevPct=pct
            else:
                printedBool=False
        print "tde file built to:",tdefileName
        endTime=datetime.datetime.now()
        print "End Time:",endTime
        diff=endTime - startTime 
        print "Build elapsed time:", diff
    def push(self):
        try:
            tdeS.ServerAPI.initialize()
            conn=tdeS.ServerConnection()
            password=decodeWord(self.tde_settings_ins.server_password)            
            conn.connect(self.tde_settings_ins.server_address,self.tde_settings_ins.server_login,password,"")
            conn.publishExtract(self.tde_settings_ins.tde_file,'default',self.tde_settings_ins.tde_file,True)
            conn.close()
            tdeS.ServerAPI.cleanup()
            print "Uploaded to server:",self.tde_settings_ins.server_address
            
        except tdeE.TableauException, e:
            # Handle the exception depending on the type of exception received

            errorMessage = "Error: "

            if e.errorCode == tde.Result.INTERNAL_ERROR:
                errorMessage += "INTERNAL_ERROR - Could not parse the response from the server."

            elif e.errorCode == tde.Result.INVALID_ARGUMENT:
                errorMessage += "INVALID_ARGUMENT - " + e.message

            elif e.errorCode == tde.Result.CURL_ERROR:
                errorMessage += "CURL_ERROR - " + e.message

            elif e.errorCode == tde.Result.SERVER_ERROR:
                errorMessage += "SERVER_ERROR - " + e.message

            elif e.errorCode == tde.Result.NOT_AUTHENTICATED:
                errorMessage += "NOT_AUTHENTICATED - " + e.message

            elif e.errorCode == tde.Result.BAD_PAYLOAD:
                errorMessage += "BAD_PAYLOAD - Unknown response from the server. Make sure this version of Tableau API is compatible with your server."

            elif e.errorCode == tde.Result.INIT_ERROR:
                errorMessage += "INIT_ERROR - " + e.message

            else:
                errorMessage += "An unknown error occured."

            print errorMessage

        

def main(argv):
        
    parseArgs = parseInOut(argv[1:])
    if parseArgs.PFound==True:
        print "encoded password: ",encodeWord(parseArgs.password)
    #    print "decoded password: ",decodeWord(encodeWord(parseArgs.password))
    else:
        mytdeSettings=tdeSettings.fromfilename(parseArgs.inputfile,parseArgs.dictParams)
        mybuilder=builder(mytdeSettings)
        mybuilder.build()
        if mytdeSettings.serverUpload==True:
            mybuilder.push()
    
    
if __name__=="__main__":
    main(sys.argv)
