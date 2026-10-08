#!/usr/bin/env python3
"""Pulls the sound out of a Godot Movie Maker AVI (MJPEG video, PCM audio) into a WAV, with no other tools.

  python3 tools/avi_audio.py <movie.avi> <out.wav>

Godot writes one audio chunk ("01wb") after each frame ("00dc"); the WAV keeps the stream's own format.
"""
import struct
import sys
import wave


def chunks(f, end):
	while f.tell() + 8 <= end:
		cid, size = struct.unpack("<4sI", f.read(8))
		start = f.tell()
		yield cid, size, start
		f.seek(start + size + (size & 1))


def main() -> None:
	src, dst = sys.argv[1], sys.argv[2]
	fmt = None
	pcm = bytearray()
	with open(src, "rb") as f:
		riff, size, kind = struct.unpack("<4sI4s", f.read(12))
		assert riff == b"RIFF" and kind == b"AVI ", "not an AVI"
		stack = [(f.tell(), 12 + size - 4)]
		def walk(end):
			nonlocal fmt, pcm
			for cid, size, start in chunks(f, end):
				if cid == b"LIST":
					f.seek(start)
					f.read(4)   # the list's type
					walk(start + size)
					f.seek(start + size + (size & 1))
				elif cid == b"strf" and size >= 16 and fmt is None:
					f.seek(start)
					data = f.read(size)
					tag, channels, rate, _, align, bits = struct.unpack("<HHIIHH", data[:16])
					if tag == 1:   # PCM: the audio stream's format (the video's strf is a bitmap header)
						fmt = (channels, rate, bits)
				elif cid[2:] == b"wb":
					f.seek(start)
					pcm += f.read(size)
		walk(12 + size - 4 + 8)
	if fmt is None:
		raise SystemExit("avi_audio: no PCM audio stream in %s" % src)
	channels, rate, bits = fmt
	with wave.open(dst, "wb") as w:
		w.setnchannels(channels)
		w.setsampwidth(bits // 8)
		w.setframerate(rate)
		w.writeframes(bytes(pcm))
	print("avi_audio: %s (%d ch, %d Hz, %d bit, %.1f s)" % (dst, channels, rate, bits, len(pcm) / (channels * bits // 8) / rate))


if __name__ == "__main__":
	main()
