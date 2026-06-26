# Future Terraform Deployment

Terraform is planned after the single-account Windows deployment is stable. Do not put Exness passwords, OpenAI keys, or Windows administrator passwords in Terraform source or Git state.

## Planned AWS Resources

- Lightsail or EC2 Windows instance
- static IPv4 address
- security group/firewall rules for 80 and later 443
- restricted RDP administration source ranges
- optional S3 bucket for versioned installers
- encrypted secrets in AWS Systems Manager Parameter Store or Secrets Manager
- DNS record and TLS termination
- CloudWatch disk/CPU/process alarms

## Provisioning Split

Terraform should create infrastructure only. A signed PowerShell bootstrap should configure Windows:

1. Install Git, Node.js, Python, Exness MT5, and Nginx.
2. Clone a pinned AegisTrade release tag.
3. Retrieve secrets at runtime using an instance role.
4. Build the API/dashboard.
5. Register persistent scheduled tasks.
6. Run health checks.

MT5 login still requires an interactive Windows user session unless a later orchestration layer provisions isolated desktop sessions.

## Multi-User Direction

Each trading account should receive:

- a database account record
- encrypted broker credentials
- an isolated Windows user/session or dedicated worker host
- a unique `MT5_ACCOUNT_ID`
- its own `runtime/accounts/<account_id>` bridge
- per-account risk settings and subscription entitlements

The web/API tier can move to inexpensive Linux hosting later. Windows capacity should scale only with active MT5 sessions, which is the primary cost driver.

## Readiness Gate

Create Terraform only after:

- reboot recovery is tested
- worker snapshots remain healthy for several days
- demo-only execution logs are reviewed
- backup/restore and secret rotation are documented
- the Windows image/bootstrap is pinned and repeatable
