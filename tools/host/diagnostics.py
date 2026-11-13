"""Report the file field that caused a host-side rejection."""


class Rejection(ValueError):
    def __init__(self, code, offset, field, region=None):
        super().__init__(code)
        self.code = code
        self.offset = offset
        self.field = field
        self.region = region

    def report(self):
        result = dict(Code=self.code, Offset=self.offset, Field=self.field)
        if self.region is not None:
            result['RegionIndex'] = self.region
        return result
