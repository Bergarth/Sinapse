using Grpc.Core;
using Grpc.Net.Client;
using Sinapse.Contracts.V1;

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

    public async Task<DaemonConnectionResult> GetStartupStatusAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            using var channel = GrpcChannel.ForAddress(_daemonEndpoint);
            var client = new DaemonContract.DaemonContractClient(channel);
            var response = await client.HealthCheckAsync(
                new HealthCheckRequest { Requester = "desktop-shell" },
                cancellationToken: cancellationToken);

            var isConnected = response.Daemon.Status == HealthStatus.Healthy;
            var lastSuccessfulConnectionUtc = isConnected ? DateTimeOffset.UtcNow : null;

            return new DaemonConnectionResult(
                IsConnected: isConnected,
                Endpoint: _daemonEndpoint,
                DaemonStatus: response.Daemon.Detail,
                DaemonVersion: response.DaemonVersion,
                EnvironmentStatus: response.System.Detail,
                EnvironmentName: response.System.Environment,
                LastSuccessfulConnectionUtc: lastSuccessfulConnectionUtc,
                ErrorMessage: null);
        }
        catch (RpcException ex)
        {
            return DisconnectedResult(_daemonEndpoint, ex.Status.Detail);
        }
        catch (Exception ex)
        {
            return DisconnectedResult(_daemonEndpoint, ex.Message);
        }
    }

    private static DaemonConnectionResult DisconnectedResult(string endpoint, string errorDetail)
    {
        return new DaemonConnectionResult(
            IsConnected: false,
            Endpoint: endpoint,
            DaemonStatus: "Unavailable",
            DaemonVersion: "unknown",
            EnvironmentStatus: "Unavailable",
            EnvironmentName: "unknown",
            LastSuccessfulConnectionUtc: null,
            ErrorMessage: $"Could not connect to daemon: {errorDetail}");
    }
}

public sealed record DaemonConnectionResult(
    bool IsConnected,
    string Endpoint,
    string DaemonStatus,
    string DaemonVersion,
    string EnvironmentStatus,
    string EnvironmentName,
    DateTimeOffset? LastSuccessfulConnectionUtc,
    string? ErrorMessage);
