"""Report the file field that caused a host-side rejection."""


class Rejection(ValueError):
    def __init__(self, code, offset, field, region=None, *, actual=None, limit=None):
        super().__init__(code)
        self.code = code
        self.offset = offset
        self.field = field
        self.region = region
        self.actual = actual
        self.limit = limit
        self.admission = None

    def report(self):
        result = dict(Code=self.code, Offset=self.offset, Field=self.field)
        if self.region is not None:
            result['RegionIndex'] = self.region
        if self.limit is not None:
            result.update(ActualBytes=self.actual, LimitBytes=self.limit)
        return result
