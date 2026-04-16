#!/bin/bash
# Seeds API keys and bot tokens for CI/test environments
# Run this after services are up to configure cross-service authentication
set -e

echo "🔑 Setting up test authentication tokens..."

# Wait for MongoDB to be ready
echo "Waiting for MongoDB..."
until mongosh --host mongodb:27017 --eval "db.adminCommand('ping')" >/dev/null 2>&1; do
  echo "  MongoDB not ready, retrying..."
  sleep 2
done
echo "✓ MongoDB is ready"

# Seed Censer bot token for Postern/Billing API → Censer admin API
echo "Seeding Censer bot token..."
mongosh --quiet --host mongodb:27017 stoat <<'EOF'
try {
  db.bot_tokens.insertOne({
    token_hash: "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIxF3k0C1.", // bcrypt hash of "test_bot_token"
    name: "test-bot-postern",
    permissions: ["admin", "create_server", "update_tier"],
    created_at: new Date(),
    enabled: true
  });
  print("✓ Censer bot token seeded");
} catch (e) {
  if (e.code === 11000) {
    print("  Bot token already exists, skipping");
  } else {
    throw e;
  }
}
EOF

# Seed Unveil API key for Postern/Billing API → Unveil admin API
# Note: Unveil stores API keys in Postgres - will be added via migration
# For now, we'll seed via environment variable in docker-compose
echo "✓ Unveil API key configured via environment"

# Seed test subscription data for billing scenarios
echo "Seeding billing test data..."
mongosh --quiet --host mongodb:27017 stoat <<'EOF'
try {
  // Find alice user ID (created by seed script)
  var alice = db.users.findOne({username: "alice"});
  if (!alice) {
    print("⚠️  Warning: alice user not found, skipping billing test data");
  } else {
    // Insert test subscription
    db.subscriptions.insertOne({
      user_id: alice._id,
      tier: "free",
      status: "active",
      stripe_customer_id: "cus_test_alice",
      created_at: new Date(),
      updated_at: new Date()
    });

    // Insert test server ownership
    var testServer = db.servers.findOne({name: "Test Community"});
    if (testServer) {
      db.server_ownerships.insertOne({
        user_id: alice._id,
        server_id: testServer._id,
        tier: "free",
        created_at: new Date()
      });
    }

    print("✓ Billing test data seeded");
  }
} catch (e) {
  if (e.code === 11000) {
    print("  Test data already exists, skipping");
  } else {
    print("⚠️  Warning: " + e.message);
  }
}
EOF

echo "✅ Test authentication setup complete"
