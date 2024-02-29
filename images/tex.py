#!/usr/bin/env python
# -*- coding: utf-8 -*-
from struct import unpack, pack
from io import BytesIO
from PIL import Image
import lz4.block
import sys
import os

# https://gist.github.com/FiddyFive/ca6d110823f7dce31bc8d2884e9fdc0f

class Tex:
    SIGN = b'\xed\x03\x00\x00'

    def __init__(self, read_io=None):
        if read_io is not None:
            self.load(read_io)

    def load(self, read_io):
        # Read 4 bytes. Address now 0x04
        if read_io.read(len(self.SIGN)) != self.SIGN:
            raise TypeError('wrong file type')
        
        # Read 0x4 bytes. Address now 0x8.
        self.imageCount, = unpack("<I", read_io.read(4))

        for i in range(self.imageCount):
            # Read 0xC (12) bytes. Address now 0x14.
            self.imageData[i].width, self.imageData[i].height, self.imageData[i].type = unpack("<3I", read_io.read(0xc))
            
            # Skip over 0x34 bytes of unneeded data. Address now 0x48.
            self.imageData[i].dummy = read_io.read(0x34)
            zsize, = unpack('<I', read_io.read(4))
            self.imageData[i].zbuf = read_io.read(zsize)

    def save(self, write_io):
        write_io.write(self.SIGN)
        write_io.write(self.imageCount)
        for i in range (self.imageCount):
            write_io.write(pack("<3I", self.imageData[i].width, self.imageData[i].height, self.imageData[i].type))
            write_io.write(self.imageData[i].dummy)
            write_io.write(pack('<I', len(self.imageData[i].zbuf)))
            write_io.write(self.imageData[i].zbuf)

    @property
    def image(self):
        
        size = self.imageData[i].width * self.imageData[i].height
        if self.imageData[i].type == 1:
            image_type = 'L'
        elif self.imageData[i].type == 2:
            image_type = 'RGBA'
            size *= 4
        else:
            raise TypeError('unknown type %x' % self.imageData[i].type)

        buf = lz4.block.decompress(self.imageData[i].zbuf, uncompressed_size=size)
        im = Image.new(image_type, (self.imageData[i].width, self.imageData[i].height))
        im.frombytes(buf)
        return im.transpose(Image.FLIP_TOP_BOTTOM)

    @image.setter
    def image(self, im):
        assert(im.size == (self.width, self.height))
        buf = im.transpose(Image.FLIP_TOP_BOTTOM).tobytes()
        self.zbuf = lz4.block.compress(buf, store_size=False)


if __name__ == '__main__':
    tex = Tex(open(sys.argv[1], 'rb'))
    tex.image.save(os.path.splitext(sys.argv[1])[0] + '.png')
