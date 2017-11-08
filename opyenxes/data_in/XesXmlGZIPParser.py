from opyenxes.data_in.XesXmlParser import XesXmlParser
import gzip


class XesXmlGZIPParser(XesXmlParser):
    """Parser for the compressed XES XML serialization.

    :param factory: The XES model factory instance used to build the model from
      the serialization.
    :type factory: XFactory
    """
    def __init__(self, factory=None):
        super().__init__(factory)

    def can_parse(self, file):
        """Checks whether this parser can handle the given file.

        :param file: path of the file to check against parser.
        :type file: str
        :return: Whether this parser can handle the given file.
        :rtype: bool
        """
        return super().ends_with_ignore_case(file, ".xes.gz")

    def parse(self, file):
        """Parses a log from the given input stream, which is supposed to
        deliver an XES log in XML representation.

        :param file: file generated by the function 'open(path)', which is
          supposed to deliver an XES log in XML representation.
        :type file: _io.TextIOWrapper
        :return: The parsed list of logs.
        :rtype: list[XLog]
        """
        path = file.name
        file.close()
        with gzip.open(path) as file:
            return super().parse(file)
