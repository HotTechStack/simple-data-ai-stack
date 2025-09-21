# 🚀 Customer Data + AI Insights Pipeline

A complete n8n workflow that demonstrates modern data orchestration: **Database → Transformation → AI Analysis → Automated Reporting**

Replace fragile cron jobs with a robust, visual pipeline that your whole team can understand and modify.
<img width="1299" height="598" alt="n8n_img" src="https://github.com/user-attachments/assets/e928f2ab-1963-4731-956f-f6df49138ae3" />

## 📋 What This Pipeline Does

**Automated Customer Retention Analysis:**
- ⏰ Runs every Monday at 9AM (or trigger manually via webhook)
- 📊 Fetches active customers from your database (last 30 days)
- 🔄 Enriches data with business metrics (AOV, recency, risk scoring)
- 🤖 Uses AI to generate personalized retention strategies for high-risk customers
- 💾 Stores insights back to database for tracking
- 📱 Sends summary reports to Slack and email
- 🚨 Automatic error alerts if anything fails

## 🏗️ Architecture Overview

```
[CRON/Webhook] → [Postgres Query] → [Transform Data] → [Risk Filter]
                                          ↓
[Email Report] ← [Slack Summary] ← [Summary Report] 
                                          ↑
[Store Insights] ← [Distribute Strategies] ← [AI Analysis]
```

## 🛠️ Prerequisites

### Required Services:
- **n8n instance** (cloud or self-hosted)
- **PostgreSQL database** (or any SQL database)
- **OpenAI API key** (for AI analysis)
- **Slack workspace** (for notifications)
- **SMTP email** (for reports)

### Database Schema:
```sql
-- Main customers table (you provide this)
CREATE TABLE customers (
  customer_id INTEGER PRIMARY KEY,
  customer_name VARCHAR(255),
  email VARCHAR(255),
  total_orders INTEGER,
  total_spent DECIMAL(10,2),
  last_order_date DATE,
  customer_segment VARCHAR(50) -- 'VIP', 'Regular', 'New', etc.
);

-- Pipeline outputs (auto-created by pipeline)
CREATE TABLE customer_insights (
  customer_id INTEGER,
  customer_name VARCHAR(255),
  risk_level VARCHAR(10),
  ai_strategy TEXT,
  analysis_date DATE,
  avg_order_value DECIMAL(10,2),
  days_since_last_order INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🚀 Installation Steps

### 1. Import the Pipeline
1. Copy the JSON from the artifact above
2. In n8n: **Settings** → **Import from JSON**
3. Paste the JSON and import

### 2. Fix Missing Connection
- Connect **Error Handler** → **Send Error Alert** (this connection gets lost in import)

### 3. Set Up Credentials

#### PostgreSQL Database:
- Node: **Fetch Active Customers** & **Store AI Insights**
- Create credential: **Postgres**
- Add your database connection details

#### OpenAI API:
- Node: **AI Retention Strategy**
- Create credential: **OpenAI**
- Add your OpenAI API key from https://platform.openai.com/api-keys

#### Slack Integration:
- Nodes: **Send Slack Summary** & **Send Error Alert**
- Create credential: **Slack**
- Add Slack bot token (see Slack setup below)

#### Email SMTP:
- Node: **Send Email Report**
- Create credential: **SMTP**
- Add your email server details

### 4. Slack Setup (Optional but Recommended)
1. Go to https://api.slack.com/apps
2. **Create New App** → **From scratch**
3. Add these **Bot Token Scopes**:
   - `chat:write`
   - `chat:write.public`
4. **Install App** to your workspace
5. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
6. Use this token in n8n Slack credential

## 🧪 Testing the Pipeline

### Option 1: Manual Trigger (Recommended for first test)
1. Use the **Manual Webhook Trigger** node
2. Click **Test workflow**
3. Check each node executes successfully

### Option 2: Sample Data Insert
```sql
-- Insert test data to verify pipeline works
INSERT INTO customers VALUES 
(1, 'John Doe', 'john@example.com', 15, 1250.00, '2025-09-10', 'VIP'),
(2, 'Jane Smith', 'jane@example.com', 8, 640.00, '2025-08-15', 'Regular'),
(3, 'Bob Wilson', 'bob@example.com', 25, 3200.00, '2025-09-18', 'VIP');
```

### Option 3: Webhook URL
- After saving, the webhook node provides a URL
- POST to this URL to trigger the pipeline:
```bash
curl -X POST https://your-n8n-instance.com/webhook/trigger-customer-analysis
```

## 🎯 Customization Guide

### Modify Risk Scoring Logic
Edit the **Transform Customer Data** node:
```javascript
// Current logic in the Code node
let riskLevel = 'LOW';
if (daysSinceLastOrder > 14 && customer.customer_segment === 'VIP') {
  riskLevel = 'HIGH';
} else if (daysSinceLastOrder > 21) {
  riskLevel = 'MEDIUM';
}

// Example: Add spending-based risk
if (customer.total_spent < 100 && daysSinceLastOrder > 7) {
  riskLevel = 'HIGH';
}
```

### Change AI Prompt
Edit the **AI Retention Strategy** node prompt:
```
You are a customer success expert specializing in [YOUR INDUSTRY].
Analyze customer data and provide actionable retention strategies.
Focus on [YOUR SPECIFIC GOALS: upselling, engagement, etc.]
```

### Add More Notification Channels
- Duplicate **Send Slack Summary** node
- Change to different channels: `#sales`, `#management`
- Add Teams, Discord, or webhook notifications

### Modify Schedule
Edit **Weekly Monday 9AM** CRON node:
- Daily: `0 9 * * *`
- Bi-weekly: `0 9 * * 1/2`
- End of month: `0 9 28-31 * *`

## 📊 Understanding the Output

### Risk Levels:
- **HIGH**: VIP customers inactive >14 days, or any customer >21 days
- **MEDIUM**: Regular customers inactive 15-21 days  
- **LOW**: Active customers with recent orders

### AI Strategy Examples:
- "Send personalized discount code for their favorite product category. Follow up with phone call from account manager."
- "Invite to exclusive VIP event and offer early access to new products."

### Reports Include:
- Customer count by risk level
- Revenue metrics (AOV, total revenue)
- AI-generated retention strategies
- Clickable dashboard links

## 🔧 Troubleshooting

### Common Issues:

**"AI Retention Strategy shows question mark"**
- Missing OpenAI credentials
- Invalid API key
- Check OpenAI account has credits

**"Database connection failed"**
- Verify database credentials
- Check if database is accessible from n8n
- Confirm table schema matches

**"No customers found"**
- Check if customers table has recent data
- Verify the 30-day filter in SQL query
- Test query directly in database

**"Slack messages not sending"**
- Verify bot token is correct
- Check channel names exist (#customer-success)
- Ensure bot is added to channels

### Error Handling:
- Pipeline automatically sends Slack alerts on failures
- Check **Executions** tab in n8n for detailed error logs
- Each node shows success/failure status

## 🚀 Next Steps & Extensions

### Production Enhancements:
1. **Add data validation** before AI analysis
2. **Implement rate limiting** for API calls
3. **Add cost tracking** for OpenAI usage
4. **Create customer segments** based on behavior
5. **Build dashboard** to visualize trends

### Integration Ideas:
- **CRM sync**: Push insights to Salesforce/HubSpot
- **Email campaigns**: Trigger personalized emails via Mailchimp
- **Support tickets**: Auto-create tasks for high-risk customers
- **Analytics**: Send metrics to Google Analytics or Mixpanel

### Advanced Features:
- **A/B testing**: Track which AI strategies work best
- **Predictive modeling**: Forecast customer lifetime value
- **Real-time triggers**: React to customer behavior instantly
- **Multi-channel analysis**: Include social media, support tickets

## 📞 Support

- **Educational**: Learn modern data orchestration patterns
- **Practical**: Solve real customer retention challenges  
- **Extensible**: Easy to modify for your specific needs

For n8n-specific help: https://docs.n8n.io
For OpenAI API issues: https://platform.openai.com/docs
