using Grpc.Health.V1;
using Grpc.Net.Client;

namespace DesktopShell.Services;

public sealed class DaemonConnectionService
{
    private readonly string _daemonEndpoint;

    public DaemonConnectionService(string? daemonEndpoint = null)
    {
        _daemonEndpoint = daemonEndpoint
            ?? Environment.GetEnvironmentVariable("AGENT_DAEMON_ENDPOINT")
            ?? "http://127.0.0.1:50051";
    }

    public async Task<DaemonConnectionResult> CheckHealthAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            using var channel = GrpcChannel.ForAddress(_daemonEndpoint);
            var client = new Health.HealthClient(channel);
            var response = await client.CheckAsync(
                new HealthCheckRequest { Service = "sinapse.contracts.v1.DaemonContract" },
                cancellationToken: cancellationToken);

            var connected = response.Status == HealthCheckResponse.Types.ServingStatus.Serving;
            var message = connected
                ? "Connected"
                : $"Not connected (status: {response.Status})";

            return new DaemonConnectionResult(
                IsConnected: connected,
                Endpoint: _daemonEndpoint,
                StatusMessage: message,
                ErrorMessage: connected ? null : "Daemon reported an unhealthy status. Placeholder recovery flow.");
        }
        catch (Exception ex)
        {
            return new DaemonConnectionResult(
                IsConnected: false,
                Endpoint: _daemonEndpoint,
                StatusMessage: "Not connected",
                ErrorMessage: $"Could not reach daemon. Placeholder error handling: {ex.Message}");
        }
    }
}

public sealed record DaemonConnectionResult(
    bool IsConnected,
    string Endpoint,
    string StatusMessage,
    string? ErrorMessage);
