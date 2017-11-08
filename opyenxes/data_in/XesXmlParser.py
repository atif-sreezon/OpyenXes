﻿from xml.sax.handler import ContentHandler
from xml.sax import parse as xml_parse
from urllib import parse
from opyenxes.factory.XFactoryRegistry import XFactoryRegistry
from opyenxes.extension.XExtensionManager import XExtensionManager
from opyenxes.classification.XEventAttributeClassifier import XEventAttributeClassifier
from opyenxes.utils.XsDateTimeConversion import parse_date_time
from opyenxes.utils.XTokenHelper import XTokenHelper
from opyenxes.id.XID import XID
from opyenxes.model.XAttributeCollection import XAttributeCollection


class XesXmlParser:
    """Parser for the XES XML serialization.

    :param factory: The XES model factory instance used to build the model from
      the serialization.
    :type factory: XFactory
    """
    def __init__(self, factory=None):
        if factory:
            self.factory = factory
        else:
            self.factory = XFactoryRegistry().current_default()

    def can_parse(self, file):
        """Checks whether this parser can handle the given file.

        :param file: path of the file to check against parser.
        :type file: str
        :return: Whether this parser can handle the given file.
        :rtype: bool
        """
        return self.ends_with_ignore_case(file, ".xes")

    def parse(self, file):
        """Parses a log from the given input stream, which is supposed to
        deliver an XES log in XML representation.

        :param file: file generated by the function 'open(path)', which is
          supposed to deliver an XES log in XML representation.
        :type file: _io.TextIOWrapper
        :return: The parsed list of logs.
        :rtype: list[XLog]
        """
        handler = XesXmlParser.XesXmlHandler()

        xml_parse(file, handler)

        return [handler.get_log()]

    @staticmethod
    def ends_with_ignore_case(name, suffix):
        """Returns whether the given file name ends (ignoring the case) with the
        given suffix.

        :param name: The given file name.
        :type name: str
        :param suffix: The given suffix.
        :type suffix: str
        :return: Whether the given file name ends (ignoring the case) with the given suffix.
        :rtype: bool
        """
        i = len(name) - len(suffix)

        if i > 0:
            return suffix in name[i:]
        return False

    class XesXmlHandler(ContentHandler):
        """SAX handler class for XES in XML representation.

        """
        def __init__(self):
            super().__init__()
            self.__log = None
            self.__trace = None
            self.__event = None
            self.__attribute_stack = list()  # stack
            self.__attributable_stack = list()  # stack
            self.__extension = set()
            self.__globals = None
            self.__last = None

        def get_log(self):
            """Retrieves the parsed log.

            :return: The parsed log.
            :rtype: XLog
            """
            return self.__log

        def startElement(self, element_name, attributes):
            """ Overrides startElement in class ContentHandler

            :param element_name: Contains the raw XML 1.0 name of the element type.
            :type element_name: str
            :param attributes: An instance of the Attributes class containing
              the attributes of the element
            :type attributes: xml.sax.xmlreader.AttributesImpl
            """
            tag_name = element_name.lower()
            if tag_name not in ["string", "date", "int", "float", "boolean", "id", "list", "container"]:
                if tag_name == "event":
                    self.__event = XesXmlParser().factory.create_event()
                    self.__attributable_stack.append(self.__event)
                elif tag_name == "trace":
                    self.__trace = XesXmlParser().factory.create_trace()
                    self.__attributable_stack.append(self.__trace)
                elif tag_name == "log":
                    self.__log = XesXmlParser().factory.create_log()
                    self.__attributable_stack.append(self.__log)
                elif tag_name == "extension":
                    extension = None

                    prefix = attributes.get("prefix")
                    keys = attributes.get("uri")

                    if prefix is not None:
                        extension = XExtensionManager().get_by_prefix(prefix)

                    elif keys is not None:
                        extension = XExtensionManager().get_by_uri(parse.urlparse(keys))

                    if extension is not None:
                        self.__log.get_extensions().add(extension)
                    else:
                        print("Unknown extension: " + keys)

                elif tag_name == "global":

                    name = attributes.get("scope")

                    if name.lower() == "trace":
                        self.__globals = self.__log.get_global_trace_attributes()
                    elif name.lower() == "event":
                        self.__globals = self.__log.get_global_event_attributes()

                elif tag_name == "classifier":
                    name = attributes.get("name")
                    keys = attributes.get("keys")
                    if name is not None and keys is not None and len(name) > 0 and len(keys) > 0:
                        array = XTokenHelper.extract_tokens(keys)
                        classifier = XEventAttributeClassifier(name, array)
                        self.__log.get_classifiers().append(classifier)
            else:
                name = attributes.get("key")
                if name is None:
                    name = "UNKNOWN"

                value = attributes.get("value")
                if value is None:
                    value = ""

                keys_list = None
                if ":" in name:
                    prefix = name[:name.index(":")]
                    keys_list = XExtensionManager().get_by_prefix(prefix)

                attribute = None

                if tag_name == "string":
                    attribute = XesXmlParser().factory.create_attribute_literal(name, value, keys_list)

                elif tag_name == "date":
                    var15 = parse_date_time(value)
                    if var15 is None:
                        return
                    attribute = XesXmlParser().factory.create_attribute_timestamp(name, var15, keys_list)

                elif tag_name == "int":
                    attribute = XesXmlParser().factory.create_attribute_discrete(name, int(value), keys_list)

                elif tag_name == "float":
                    attribute = XesXmlParser().factory.create_attribute_continuous(name, float(value), keys_list)

                elif tag_name == "boolean":
                    var16 = True if value.lower() == "true" else False
                    attribute = XesXmlParser().factory.create_attribute_boolean(name, var16, keys_list)

                elif tag_name == "id":
                    attribute = XesXmlParser().factory.create_attribute_id(name, XID.parse(value), keys_list)

                elif tag_name == "list":
                    attribute = XesXmlParser().factory.create_attribute_list(name, keys_list)

                elif tag_name == "container":
                    attribute = XesXmlParser().factory.create_attribute_container(name, keys_list)

                if attribute is not None:
                    self.__attribute_stack.append(attribute)
                    self.__attributable_stack.append(attribute)

        def endElement(self, local_name):
            """ Overrides endElement in class ContentHandler

            :param local_name: The name of the element type, just as with the startElement event
            :type local_name: str
            """
            tag_name = local_name

            if tag_name.lower() == "global":
                self.__globals = None

            elif tag_name.lower() not in ["string", "date", "int", "float", "boolean", "id", "list", "container"]:
                if tag_name.lower() == "event":
                    self.__trace.append(self.__event)
                    self.__event = None
                    self.__attributable_stack.pop()
                elif tag_name.lower() == "trace":
                    self.__log.append(self.__trace)
                    self.__trace = None
                    self.__attributable_stack.pop()

                elif tag_name.lower() == "log":
                    for extension in self.__extension:
                        self.__log.get_extensions().add(extension)
                    self.__attributable_stack.pop()

            else:
                i = self.__attribute_stack.pop()
                self.__attributable_stack.pop()

                if self.__globals is not None:

                    self.__globals.append(i)
                else:
                    self.__attributable_stack[-1].get_attributes()[i.get_key()] = i
                    if len(self.__attribute_stack) != 0 and\
                            isinstance(self.__attribute_stack[-1], XAttributeCollection):

                        self.__attribute_stack[-1].add_to_collection(i)
