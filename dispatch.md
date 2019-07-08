## Http Input Dispatching Decorator

The purpose of _dispatch_ decorator was initially 'dispatching' the http input to python function parameters.
But when trying to implement this feature implies deserialization, validation and error handling. Therefore,
the decorator performs all the following items:

- Filling the function parameters throughout http input
- Validating the input data using [Cerberus Validator](https://docs.python-cerberus.org/en/stable/)
- Items get deserialized using fastest JSON parser: [Rapid JSON](https://pypi.org/project/python-rapidjson/)

Any error during  dispatching parameters from input data raises with English error message and HTTP status of
Bad Request (400).


#### Http Input Data

1. From URI:

    The parameter can be read from QueryString (?key=value&...) or via path placeholders (i.e. resource_id parameter in ‍‍‍‍```/resources/{resource_id}```)
    Any parameter can be a sequence (```/resources/1,2,3,4```) or a a single item.

2. From request body:

    Request body is parsed using HTTP header values: Content-Type is parsed for the format of body data.
    The data can be url-encoded-form-data or json/messagepack/cbor/...
    
3. From http header:
    
    If you need some input parameter read from http header, you must inform the decorator using argument from_header.
    
    **_Hint: The parameters are read in the following order: header, body, querystring. It means the duplicate parameters are overriden when read again._**
    

#### Function parameters

1. Argument with primitive type hint (Annotation)
    
    Function arguments with type hints are parsed and validated using type annotation. For example, int, float, enum... 
    Supported type annotations is described below.
    
2. Argument with Python class type hint

    If the type annotation is some Python class (including SqlAlchemy model types), the parameters would be dispatched into its fields (properties) instead of the 
    argument name. Each class field works like a single function argument with the same name.
    
    **_Hint: If we have both hints, that is a single parameter with the same name of the class field, both are filled._**
    
3. QueryString parameter

    This argument is filled with the complete URI QueryString (Anything after question mark) and is marked with 
    query_string_arg in dispatch decorator.
    
    **_Hint: All arguments can be optional. If some argument gets optional, the default parameter would be filled if the corresponding http input is empty._**
    
    
#### Supported Argument/Field Types
 
 - int, float, bool : Primitive Python types are supported both as type annotation and SqlAlchemy column type. Note that the type annotation can be used both in function argument and Python data class field.
 
 - str, bytes: string-like types are supported alongside with encoding. bytes type can get image and other binary data with help of _binary_ argument of dispatch decorator.
 - enum: Python built-in enum type is supported: the http input values are parsed into enuk items.
 - datetime, date, time: These three types are parsed using ISO format into Python standard type.
 - tuple, list: Parameters containing more than one item can be expected as Python standard sequence.
 
 
 
#### Validation


By default, all arguments are validated during parsing. If you want some regular expression pattern for string parsing, you can add column info item with key 'pattern' within SqlAlchemy column line. Other validations can be added using Cerberus package.
