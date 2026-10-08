// Joins a folder of numbered frames (JPEG or PNG, sorted by name) into an H.264 MP4, with an optional music track
// trimmed to the video's length and faded out at the end. Uses the Mac's own encoder (AVFoundation), so nothing
// needs installing.
//
//   swiftc -O tools/encode.swift -o build/encode
//   build/encode --frames <dir> --out <file.mp4> [--fps 30] [--bitrate 12000000]
//                [--audio <file>] [--audio-start <s>] [--fade <s>] [--gain <0..1>]
import AVFoundation
import CoreImage
import Foundation
import ImageIO

func fail(_ message: String) -> Never {
	FileHandle.standardError.write(("encode: " + message + "\n").data(using: .utf8)!)
	exit(1)
}

var args: [String: String] = [:]
var i = 1
while i < CommandLine.arguments.count {
	let key = CommandLine.arguments[i]
	guard key.hasPrefix("--"), i + 1 < CommandLine.arguments.count else { fail("bad argument \(key)") }
	args[String(key.dropFirst(2))] = CommandLine.arguments[i + 1]
	i += 2
}
guard let framesDir = args["frames"], let outPath = args["out"] else {
	fail("usage: --frames <dir> --out <file.mp4> [--fps 30] [--audio <file>]")
}
let fps = Int32(args["fps"] ?? "30") ?? 30
let bitrate = Int(args["bitrate"] ?? "12000000") ?? 12_000_000
let fm = FileManager.default
let frames = try! fm.contentsOfDirectory(atPath: framesDir)
	.filter { $0.hasSuffix(".jpg") || $0.hasSuffix(".png") }
	.sorted()
	.map { (framesDir as NSString).appendingPathComponent($0) }
guard !frames.isEmpty else { fail("no frames in \(framesDir)") }

func loadImage(_ path: String) -> CGImage {
	guard let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil),
		let img = CGImageSourceCreateImageAtIndex(src, 0, nil)
	else { fail("can't read \(path)") }
	return img
}

let first = loadImage(frames[0])
let width = first.width
let height = first.height
let silentPath = outPath + ".video.mp4"
try? fm.removeItem(atPath: silentPath)
try? fm.removeItem(atPath: outPath)

// 1. The frames into a silent H.264 file.
let writer = try! AVAssetWriter(outputURL: URL(fileURLWithPath: silentPath), fileType: .mp4)
let input = AVAssetWriterInput(mediaType: .video, outputSettings: [
	AVVideoCodecKey: AVVideoCodecType.h264,
	AVVideoWidthKey: width,
	AVVideoHeightKey: height,
	AVVideoCompressionPropertiesKey: [
		AVVideoAverageBitRateKey: bitrate,
		AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
		AVVideoMaxKeyFrameIntervalKey: Int(fps) * 2,
	],
	AVVideoColorPropertiesKey: [
		AVVideoColorPrimariesKey: AVVideoColorPrimaries_ITU_R_709_2,
		AVVideoTransferFunctionKey: AVVideoTransferFunction_ITU_R_709_2,
		AVVideoYCbCrMatrixKey: AVVideoYCbCrMatrix_ITU_R_709_2,
	],
])
input.expectsMediaDataInRealTime = false
let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [
	kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
	kCVPixelBufferWidthKey as String: width,
	kCVPixelBufferHeightKey as String: height,
])
writer.add(input)
writer.startWriting()
writer.startSession(atSourceTime: .zero)
let ci = CIContext(options: [.workingColorSpace: CGColorSpace(name: CGColorSpace.sRGB)!])
let sRGB = CGColorSpace(name: CGColorSpace.sRGB)!
for (n, path) in frames.enumerated() {
	autoreleasepool {
		while !input.isReadyForMoreMediaData { usleep(2000) }
		var buffer: CVPixelBuffer?
		CVPixelBufferPoolCreatePixelBuffer(nil, adaptor.pixelBufferPool!, &buffer)
		guard let pb = buffer else { fail("no pixel buffer") }
		ci.render(CIImage(cgImage: loadImage(path)), to: pb, bounds: CGRect(x: 0, y: 0, width: width, height: height),
			colorSpace: sRGB)
		if !adaptor.append(pb, withPresentationTime: CMTime(value: CMTimeValue(n), timescale: fps)) {
			fail("frame \(n): \(writer.error?.localizedDescription ?? "?")")
		}
		if n % 300 == 0 { print("encode: frame \(n) / \(frames.count)") }
	}
}
input.markAsFinished()
let done = DispatchSemaphore(value: 0)
writer.finishWriting { done.signal() }
done.wait()
guard writer.status == .completed else { fail("video: \(writer.error?.localizedDescription ?? "?")") }
let duration = CMTime(value: CMTimeValue(frames.count), timescale: fps)

// 2. The music, trimmed and faded, laid under it.
guard let audioPath = args["audio"] else {
	try! fm.moveItem(atPath: silentPath, toPath: outPath)
	print("encode: \(outPath) (\(frames.count) frames, no audio)")
	exit(0)
}
let comp = AVMutableComposition()
let videoAsset = AVURLAsset(url: URL(fileURLWithPath: silentPath))
let audioAsset = AVURLAsset(url: URL(fileURLWithPath: audioPath))
let sem = DispatchSemaphore(value: 0)
var vTrack: AVAssetTrack?
var aTrack: AVAssetTrack?
Task {
	vTrack = try? await videoAsset.loadTracks(withMediaType: .video).first
	aTrack = try? await audioAsset.loadTracks(withMediaType: .audio).first
	sem.signal()
}
sem.wait()
guard let vt = vTrack, let at = aTrack else { fail("can't read the tracks") }
let audioStart = CMTime(seconds: Double(args["audio-start"] ?? "0") ?? 0, preferredTimescale: 600)
let cv = comp.addMutableTrack(withMediaType: .video, preferredTrackID: kCMPersistentTrackID_Invalid)!
try! cv.insertTimeRange(CMTimeRange(start: .zero, duration: duration), of: vt, at: .zero)
let ca = comp.addMutableTrack(withMediaType: .audio, preferredTrackID: kCMPersistentTrackID_Invalid)!
try! ca.insertTimeRange(CMTimeRange(start: audioStart, duration: duration), of: at, at: .zero)
let mix = AVMutableAudioMix()
let params = AVMutableAudioMixInputParameters(track: ca)
let gain = Float(args["gain"] ?? "1") ?? 1
let fade = Double(args["fade"] ?? "3") ?? 3
params.setVolume(gain, at: .zero)
let fadeStart = CMTimeSubtract(duration, CMTime(seconds: fade, preferredTimescale: 600))
params.setVolumeRamp(fromStartVolume: gain, toEndVolume: 0,
	timeRange: CMTimeRange(start: fadeStart, duration: CMTime(seconds: fade, preferredTimescale: 600)))
mix.inputParameters = [params]
guard let export = AVAssetExportSession(asset: comp, presetName: AVAssetExportPresetPassthrough) else {
	fail("no export session")
}
// Passthrough keeps the video as encoded; the audio is re-encoded to AAC so the fade can apply.
export.outputURL = URL(fileURLWithPath: outPath)
export.outputFileType = .mp4
export.audioMix = mix
export.shouldOptimizeForNetworkUse = true
let exported = DispatchSemaphore(value: 0)
export.exportAsynchronously { exported.signal() }
exported.wait()
if export.status != .completed {
	// Passthrough can't apply an audio mix on every system; fall back to the highest-quality preset.
	try? fm.removeItem(atPath: outPath)
	guard let hq = AVAssetExportSession(asset: comp, presetName: AVAssetExportPresetHighestQuality) else {
		fail("no export session")
	}
	hq.outputURL = URL(fileURLWithPath: outPath)
	hq.outputFileType = .mp4
	hq.audioMix = mix
	hq.shouldOptimizeForNetworkUse = true
	let again = DispatchSemaphore(value: 0)
	hq.exportAsynchronously { again.signal() }
	again.wait()
	guard hq.status == .completed else { fail("export: \(hq.error?.localizedDescription ?? "?")") }
}
try? fm.removeItem(atPath: silentPath)
print("encode: \(outPath) (\(frames.count) frames, \(Double(frames.count) / Double(fps)) s, music from \(audioPath))")
