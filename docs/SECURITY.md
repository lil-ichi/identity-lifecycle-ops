# 🛡️ Security & Zero-Trust IAM Policy: IdentityLifecycle Ops

## 1. Principles of Least Privilege (PoLP)
1. **Dynamic Group Mapping**: Users are never granted direct repository or cloud permissions; all access is mediated through mapped IAM groups and GitHub teams.
2. **Short-Lived STS Credentials**: AWS access defaults to temporary assumed roles rather than static long-lived IAM access keys.

---

## 2. Cryptographic Ledger Proofs
Every identity state change is anchored in a chained block ledger:
$$\text{Block}_n = \text{SHA-256}\Big(\text{Index}_n \,\|\, \text{Timestamp} \,\|\, \text{Action} \,\|\, \text{Target} \,\|\, \text{Actor} \,\|\, \text{Payload} \,\|\, \text{Hash}_{n-1}\Big)$$

Any unauthorized modification of historical database rows immediately breaks the sequential hash chain during auditor verification.
