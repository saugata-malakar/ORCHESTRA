# Claude Privacy, Safety & Legal

## Conversation Management

### Delete or Rename a Conversation
To delete or rename an individual conversation:
1. Navigate to the conversation you want to delete or rename.
2. Click on the name of the conversation at the top of the screen.
3. Select either "Delete" or "Rename" from the options that appear.

To delete multiple conversations at once:
1. Navigate to your Recents by hovering over the left side of your window and selecting "View all."
2. Hover over the conversations you want to delete, and check the selection box.
3. Click on the "Delete Selected" button.

### Incognito Chats
- Use incognito chats for sensitive conversations.
- Incognito chats are not used to improve Claude, even if Model Improvement is enabled.
- Incognito chats are not stored in your conversation history.

## Privacy and Data

### Who Can View My Conversations?
This applies to consumer products (Claude Free, Pro, Max).

When you allow data to be used to improve Claude:
- Data is automatically de-linked from your user ID before review.
- Access is limited to a small number of personnel involved in model training.
- Tools and processes filter or obfuscate sensitive data.
- Data is used solely to make Claude better — not for marketing, profiling, or selling.
- You maintain full control and can adjust privacy settings at any time at claude.ai/settings/data-privacy-controls.
- Incognito chats are never used for improvement.

Safety classifiers may still review conversations flagged for trust and safety purposes.

### Recommended: Be Mindful with Sensitive Information
Avoid sharing:
- Financial information (SSN, credit card numbers, bank account details)
- Health records or medical information
- Passwords or private login credentials
- Confidential business or personal documents

### How Long Is Data Used?
Data used for model improvement is retained as described in Anthropic's privacy policy. You can adjust your Model Improvement settings at any time. Changes apply to future conversations. For data already submitted, you can request deletion by contacting support.

To change privacy settings:
1. Go to claude.ai/settings/data-privacy-controls.
2. Toggle Model Improvement on or off.
3. Changes take effect immediately for future conversations.

## Web Crawling

### Does Anthropic Crawl the Web?
Anthropic uses three bots:
1. **ClaudeBot**: Collects web content for AI model training. Block via robots.txt to exclude your site from training data.
2. **Claude-User**: Accesses websites when users ask Claude questions. Disabling prevents content retrieval for user queries.
3. **Claude-SearchBot**: Indexes content for search. Disabling reduces visibility in search results.

To block a bot from your website, add to robots.txt:
```
User-agent: ClaudeBot
Disallow: /
```

To limit crawling speed:
```
User-agent: ClaudeBot
Crawl-delay: 1
```

Anthropic respects robots.txt directives and does not bypass CAPTCHAs.
Contact privacy@anthropic.com for crawling concerns.

## Responsible Disclosure / Bug Bounty
If you find a security vulnerability in Claude:
- Report it through Anthropic's Responsible Disclosure Policy at anthropic.com/responsible-disclosure-policy.
- Do NOT publicly disclose vulnerabilities before they are addressed.
- Anthropic evaluates reports and may offer rewards for qualifying discoveries.
- Contact security@anthropic.com for urgent security issues.

## Safeguards
- Claude has built-in safety measures to prevent harmful outputs.
- Content filtering policies may block certain outputs.
- If you receive an "Output blocked by content filtering policy" error, the request may have triggered safety filters.
- Claude is designed to decline requests for harmful, illegal, or dangerous content.

## Claude for Education
- Claude for Education provides LTI (Learning Tools Interoperability) integration for educational institutions.
- Professors and administrators can set up Claude access for students through their LMS (Learning Management System).
- To set up an LTI key, contact Anthropic's education team or visit the Claude for Education support page.
- Education accounts have specific data privacy protections for student data (FERPA compliance).
- Contact education@anthropic.com or visit support.claude.com for LTI setup instructions.

## Amazon Bedrock Integration
- Claude is available through Amazon Bedrock.
- For issues with Claude via AWS Bedrock, check:
  1. AWS service health dashboard for Bedrock status.
  2. Your AWS IAM permissions and Bedrock model access.
  3. API endpoint configuration and region settings.
  4. Rate limits on your AWS account.
- For persistent Bedrock issues, contact AWS support (not Anthropic) as AWS manages the Bedrock service.
- Anthropic provides the model; AWS manages the infrastructure and API.
