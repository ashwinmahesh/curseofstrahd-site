// Prints a music file's loudness every quarter second (RMS in dB), to place the trailer's cuts on the music.
//   swiftc -O tools/envelope.swift -o build/envelope && build/envelope <file>
import AVFoundation
let url = URL(fileURLWithPath: CommandLine.arguments[1])
let file = try! AVAudioFile(forReading: url)
let fmt = file.processingFormat
let step = AVAudioFrameCount(fmt.sampleRate / 4)
let buf = AVAudioPCMBuffer(pcmFormat: fmt, frameCapacity: step)!
var t = 0.0
while file.framePosition < file.length {
	try! file.read(into: buf, frameCount: step)
	let n = Int(buf.frameLength)
	if n == 0 { break }
	var sum: Float = 0
	for ch in 0..<Int(fmt.channelCount) {
		let p = buf.floatChannelData![ch]
		for i in 0..<n { sum += p[i] * p[i] }
	}
	let rms = sqrt(sum / Float(n * Int(fmt.channelCount)))
	print(String(format: "%6.2f %6.1f", t, 20 * log10(max(rms, 1e-6))))
	t += 0.25
}
