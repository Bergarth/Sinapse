using System.Runtime.InteropServices.WindowsRuntime;
using Windows.Media.Core;
using Windows.Media.Playback;
using Windows.Storage.Streams;

namespace DesktopShell.Services;

public sealed class SpeechPlaybackService
{
    private readonly MediaPlayer _mediaPlayer = new();

    public string LastStatus { get; private set; } = "Spoken replies are off.";

    public async Task<bool> PlayWavAsync(byte[] audioBytes)
    {
        if (audioBytes.Length == 0)
        {
            LastStatus = "No speech audio was returned by the daemon.";
            return false;
        }

        try
        {
            var stream = new InMemoryRandomAccessStream();
            await stream.WriteAsync(audioBytes.AsBuffer());
            stream.Seek(0);

            _mediaPlayer.Source = MediaSource.CreateFromStream(stream, "audio/wav");
            _mediaPlayer.Play();
            LastStatus = "Playing spoken assistant reply.";
            return true;
        }
        catch (Exception ex)
        {
            LastStatus = $"Could not play spoken reply: {ex.Message}";
            return false;
        }
    }
}
