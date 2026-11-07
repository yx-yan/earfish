// Writes everything the Mac is playing to stdout as 16 kHz mono 16-bit audio.
// Core Audio taps have no Python binding, so this small helper does the capture.

import AVFoundation
import CoreAudio
import Foundation

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("audiotap: \(message)\n".utf8))
    exit(1)
}

func check(_ status: OSStatus, _ step: String) {
    if status != noErr { fail("\(step) failed with status \(status)") }
}

func address(_ selector: AudioObjectPropertySelector) -> AudioObjectPropertyAddress {
    AudioObjectPropertyAddress(
        mSelector: selector,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )
}

func read<T>(_ object: AudioObjectID, _ selector: AudioObjectPropertySelector, as value: T) -> T {
    var result = value
    var size = UInt32(MemoryLayout<T>.size)
    var property = address(selector)
    check(AudioObjectGetPropertyData(object, &property, 0, nil, &size, &result), "reading a property")
    return result
}

let description = CATapDescription(stereoGlobalTapButExcludeProcesses: [])
description.name = "Relay"
description.isPrivate = true
description.muteBehavior = .unmuted

var tap = AudioObjectID(kAudioObjectUnknown)
check(AudioHardwareCreateProcessTap(description, &tap), "creating the tap")

let output = read(
    AudioObjectID(kAudioObjectSystemObject), kAudioHardwarePropertyDefaultSystemOutputDevice,
    as: AudioObjectID(kAudioObjectUnknown)
)
let outputUID = read(output, kAudioDevicePropertyDeviceUID, as: "" as CFString) as String

let aggregate: [String: Any] = [
    kAudioAggregateDeviceNameKey: "Relay Tap",
    kAudioAggregateDeviceUIDKey: UUID().uuidString,
    kAudioAggregateDeviceMainSubDeviceKey: outputUID,
    kAudioAggregateDeviceIsPrivateKey: true,
    kAudioAggregateDeviceIsStackedKey: false,
    kAudioAggregateDeviceTapAutoStartKey: true,
    kAudioAggregateDeviceSubDeviceListKey: [[kAudioSubDeviceUIDKey: outputUID]],
    kAudioAggregateDeviceTapListKey: [
        [kAudioSubTapUIDKey: description.uuid.uuidString, kAudioSubTapDriftCompensationKey: true]
    ],
]
var device = AudioObjectID(kAudioObjectUnknown)
check(AudioHardwareCreateAggregateDevice(aggregate as CFDictionary, &device), "creating the device")

var streamDescription = read(tap, kAudioTapPropertyFormat, as: AudioStreamBasicDescription())
guard let inputFormat = AVAudioFormat(streamDescription: &streamDescription),
    let outputFormat = AVAudioFormat(
        commonFormat: .pcmFormatInt16, sampleRate: 16_000, channels: 1, interleaved: true
    ),
    let converter = AVAudioConverter(from: inputFormat, to: outputFormat)
else { fail("unsupported tap format") }

signal(SIGPIPE, SIG_IGN)  // A closed pipe shows up as a failed write below.

var procID: AudioDeviceIOProcID?
let queue = DispatchQueue(label: "audiotap")
check(
    AudioDeviceCreateIOProcIDWithBlock(&procID, device, queue) { _, input, _, _, _ in
        guard
            let buffer = AVAudioPCMBuffer(pcmFormat: inputFormat, bufferListNoCopy: input),
            let converted = AVAudioPCMBuffer(
                pcmFormat: outputFormat,
                frameCapacity: buffer.frameLength / 2 + 64
            )
        else { return }
        var supplied = false
        var error: NSError?
        converter.convert(to: converted, error: &error) { _, status in
            if supplied {
                status.pointee = .noDataNow
                return nil
            }
            supplied = true
            status.pointee = .haveData
            return buffer
        }
        let bytes = Int(converted.frameLength) * 2
        if bytes > 0, let samples = converted.int16ChannelData?[0],
            write(STDOUT_FILENO, samples, bytes) < 0
        {
            exit(0)  // Relay stopped reading.
        }
    }, "creating the audio callback")
check(AudioDeviceStart(device, procID), "starting capture")

// A silent Mac makes no callbacks, so a failed write alone would not notice Relay is gone.
let parent = getppid()
let watchdog = DispatchSource.makeTimerSource(queue: queue)
watchdog.schedule(deadline: .now() + 1, repeating: 1)
watchdog.setEventHandler {
    if getppid() != parent { exit(0) }
}
watchdog.resume()
dispatchMain()
