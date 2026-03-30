using Windows.Media.Capture;
using Windows.Media.MediaProperties;
using Windows.Storage.Streams;

namespace DesktopShell.Services;

public sealed class PushToTalkRecorderService
{
    private MediaCapture? _mediaCapture;
    private InMemoryRandomAccessStream? _stream;
    private bool _isRecording;

    public bool IsRecording => _isRecording;

    public async Task StartRecordingAsync()
    {
        if (_isRecording)
        {
            return;
        }

        _mediaCapture = new MediaCapture();
        await _mediaCapture.InitializeAsync(new MediaCaptureInitializationSettings
        {
            StreamingCaptureMode = StreamingCaptureMode.Audio,
        });

        _stream = new InMemoryRandomAccessStream();
        await _mediaCapture.StartRecordToStreamAsync(MediaEncodingProfile.CreateWav(AudioEncodingQuality.Low), _stream);
        _isRecording = true;
    }

    public async Task<byte[]> StopRecordingAsync()
    {
        if (!_isRecording || _mediaCapture is null || _stream is null)
        {
            return [];
        }

        await _mediaCapture.StopRecordAsync();
        _isRecording = false;

        _stream.Seek(0);
        var size = (uint)_stream.Size;
        var buffer = new Buffer(size);
        await _stream.ReadAsync(buffer, size, InputStreamOptions.None);

        var bytes = new byte[buffer.Length];
        DataReader.FromBuffer(buffer).ReadBytes(bytes);

        _mediaCapture.Dispose();
        _stream.Dispose();
        _mediaCapture = null;
        _stream = null;

        return bytes;
    }
}
