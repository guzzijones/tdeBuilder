tdeBuilder

# <a id="79566006354543-_Toc442275925"></a>Introduction

## <a id="79566006354543-_Toc442275926"></a>Scope and Purpose

TdeBuilder is used to create \.tde files from input data without having to use tableau desktop\.  This allows you to schedule \.tde file creation using scheduling software\.  Data can first be joined and or modified using an ETL tool and then dumped to text files\.  Tdebuilder can read in those text files and create a TDE\.  

TDE files are compressed and indexes are created on columns that allows for faster reporting and query retrieval in Tableau Desktop\.  TDE files also use less disk space is than text files\.

## <a id="79566006354543-_Toc442275927"></a>Process Overview

1.  Create needed data using an ETL tool and output data to text files\.
2. Use tdebuilder\.py to create \.tde file
	1. Optional: set JSON settings file to upload \.tde to server
3. Open \.tde file in Tableau Desktop

## <a id="79566006354543-_Toc442275928"></a>Dependencies

1.  Tableau SDK API – downloadable from tableau
	1. Download: [http://onlinehelp\.tableau\.com/current/api/sdk/en\-us/SDK/tableau\_sdk\_installing\.htm\#downloading](http://onlinehelp.tableau.com/current/api/sdk/en-us/SDK/tableau_sdk_installing.htm%23downloading)
	2. Tableau SDK API  usage: [https://onlinehelp\.tableau\.com/current/api/sdk/en\-us/help\.htm](https://onlinehelp.tableau.com/current/api/sdk/en-us/help.htm)
	3. Tableau SDK API development: [http://onlinehelp\.tableau\.com/current/api/sdk/en\-us/SDK/Python/html/index\.html](http://onlinehelp.tableau.com/current/api/sdk/en-us/SDK/Python/html/index.html)
2. Python 2\.6 or above\.
	1. Download: [https://www\.python\.org/downloads/](https://www.python.org/downloads/)

# <a id="79566006354543-_Toc442275929"></a>JSON

JSON is built on two universal structures:

1. A collection of name and value pairs\.
2. An ordered list of values

An object is an unordered set of name and value pairs\.  An object begins with \{ \(left brace\) and ends with\} \(right brace\)\.  Each key if followed by: \(colon\) and the name value pairs are separated by, \(comma\)\.

The last entry in a list should NOT have a comma after it\.

Structure

    Object

        {}

        {members}

    Members

        Pair

        Pair,members

    Pair

        String:value

    Array

        []

        [elements]

    Elements

        Value

        Value,elements

    Value

        String

    Number

    Object

    Array

    True

    False

    Null

    Example

    "columns":{

            "Admit Date": "Date",

            "Discharge Date":"Date",

            "Patient Name": "Text",

            "Address":"Text",

            "Proc Flag":"Double"

        },

# <a id="79566006354543-_Toc442275930"></a>Configuration JSON Syntax

## <a id="79566006354543-_Toc442275931"></a>Root Keys

There root keys are as follows and are further explained in following chapters:

1.  parameters : contains a JSON of parameters
2. tde_filename
	1. Contains a string containing the filename to be output to
3. input
	1. Contains a JSON of information about the input data
4. columns
	1. Contains a JSON of column information
5. server_upload
	1. Contains a JSON of server connection information

Example:

    {

        "parameters":{

            "Entity":{

                "default":"BHM"

            },

            "fileExt":{

                "default":".txt"

            }

        },

        "tde_filename": "test_$(Entity).tde",

        "input":{

            "type": "file",

            "file_info":{

                "input_type":"starname",

                "input_file_name":"data$(fileExt)",

                "delimiter":"t",

                "column_headers":"column_headers"

                }

        },

        "columns":{

            "Admit Date": "Date",

            "Discharge Date":"Date",

            "Patient Name": "Text",

            "Address":"Text",

            "Proc Flag":"Double"

        },

        "server_upload":{

            "server_address": "https://blabla.bla.org",

            "server_login": "tableau",

            "server_password_encoded": "VFl2JnlCYUpHZ0dZe"

        }

    }

## <a id="79566006354543-_Toc442275932"></a>parameters

Parameters are used to replace text in a value\.  As an example you may want to reuse the same JSON configuration file for two similar input text files\.  Adding a parameter allows you to reuse your JSON configuration file\.  

Parameters are defined in the “parameters” key section of the configuration file\.  Reference a parameter later on in your script like so:  $\(\[name\]\)\.

Example:

    "parameters":{

        "Entity":{

            "default":"BHM"

        },

        "fileExt":{

            "default":".txt"

        }

    },

Example of this parameter being used

"tde\_filename": "test\_$\(Entity\)\.tde",

## <a id="79566006354543-_Toc442275933"></a>tde\_filename

This key is used to set the output name to be given to the \.tde file created\.

Example

    "tde_filename": "test_$(Entity).tde",

## <a id="79566006354543-_Toc442275934"></a>input

This key is used to define input type\.  Currently the only input type supported is “file”

Input types

1. Type 
	1. file - file input; if the type is file then file\_info is required
	2. file_info
		1. input\_type
			1. starname - read in a list of files using asterisks as a wildcard for multi\-file reads 
		2. input\_file\_name
			1. name of the input file or files using a wildcard asterisks
		3. delimiter
			1. delimiter used in the input file
		4. columns\_headers
			1. columns\_headers – file has column headers
			2. standard - file does not have column headers use definitions in column section to label files

Example

    "input":{

        "type": "file",

        "file_info":{

            "input_type":"starname",

            "input_file_name":"data$(fileExt)",

            "delimiter":"t",

            "column_headers":"column_headers"

            }

    },

## <a id="79566006354543-_Toc442275935"></a>columns

Column name is the key and the value is equal to the data type the column should be\.  This key is a sub key of the “input” key\.

### <a id="79566006354543-_Toc442275936"></a>Data Types

The following data types are allowed:

1. Bit
	1. Boolean True or False
	2. Example: 1,0
2. Byte
	1. A whole number
	2. Example:  123
3. Short
	1. A number with a decimal
	2. Example: 123\.222
4. Long
	1. A number with a decimal
	2. Example: 123\.222
5. Integer
	1. A whole number 
	2. Example: 1235455
6. Single
	1. A whole number
	2. Example: 55332
7. Double
	1. A number with a decimal
	2. Example: 223434\.22325423
8. Date 
	1.  A date in the required format
	2. Format: YYYY\-MM\-DD or YYYYMMDD
	3. Example: 2016\-02\-21
9. DateTime 
	1. A date and time in the required format
	2. date in format YYYY\-MM\-DD HH:MM:SS\.mm
	3. Example: 2016\-02\-02 01:05:22\.23
10. Text 
	1. long text info
	2. Example: “John Doe”
11. Memo 
	1.  long text info
	2. Example: “John Doe”

Example

    "columns":{

        "Admit Date": "Date",

        "Discharge Date":"Date",

        "Patient Name": "Text",

        "Address":"Text",

        "Proc Flag":"Double"

    },

## <a id="79566006354543-_Toc442275937"></a>server\_upload

This key is used to set server settings to upload the \.tde to tableau server\.  If this key is not in the JSON configuration the upload process is not attempted\.

        1. server_upload
        1. server_address - address of your tableau server
        2. server_login - username to log in
        3. server_password_encoded - encoded password using the –p switch via the command line.  (see Password Encode)

Example

    "server_upload":{

        "server_address": "https://bla.bla.org",

        "server_login": "tableau",

        "server_password_encoded": "VFl2JnlCYUpHZ0d"

    }

# <a id="79566006354543-_Toc442275938"></a>Password Encode

Passwords for the server upload configuration must first be scrambled using the –p switch via the command line\.

Usage:  tdeBuilder.py - [password]

The output will be the password to be entered into the server_upload  |serverpassword_encoded field in your JSON settings file\.

Example

        C:\\projects\\tableau\\extract>python tdeBuilder.py -p pass1234Blue

        encoded password:  cGFzczEyMzRCbHVl

# <a id="79566006354543-_Toc442275939">< must first be scrambled using the –p switch via the command line\.

Usage:  tdeBuilder\.py –p [password]

The output will be the password to be entered into the server\_upload  |serverpassword_encoded field in your JSON settings file\.

Example

    C:\\projects\\tableau\\extract>python tdeBuilder.py -p pass1234Blue

    encoded password:  cGFzczEyMzRCbHVl

# <a id="267754946201687-_Toc442275939"></a>Running tdeBuilder\.py

Via the command line

    python tdeBuilder.py -i [JSON configuration\]

