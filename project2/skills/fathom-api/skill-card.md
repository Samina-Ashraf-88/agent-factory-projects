## Description: <br>
Fathom API integration with managed OAuth for accessing meeting recordings, transcripts, summaries, action items, and webhooks. <br>

This skill is ready for commercial/non-commercial use. <br>

## Publisher: <br>
[byungkyu](https://clawhub.ai/user/byungkyu) <br>

### License/Terms of Use: <br>
MIT-0 <br>


## Use Case: <br>
Developers and agent users use this skill to retrieve and search Fathom meeting content, manage OAuth-backed Fathom connections, and create or delete webhook notifications for new meeting data. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: The skill can access Fathom meeting recordings, transcripts, summaries, action items, and related account data. <br>
Mitigation: Install only for the intended Fathom account, keep MATON_API_KEY private, and confirm the active connection before retrieving meeting content. <br>
Risk: Webhook and destination_url callbacks can send meeting content to external endpoints. <br>
Mitigation: Before approving callbacks, verify the destination URL, endpoint ownership, fields to be sent, and how to delete the webhook later. <br>
Risk: Create, update, and delete operations can change Fathom connections or webhooks. <br>
Mitigation: Require explicit user approval for every write operation and confirm the target resource and intended effect. <br>


## Reference(s): <br>
- [Fathom API Documentation](https://developers.fathom.ai) <br>
- [Fathom LLM Reference](https://developers.fathom.ai/llms.txt) <br>
- [Maton](https://maton.ai) <br>


## Skill Output: <br>
**Output Type(s):** [text, markdown, code, shell commands, configuration, API calls, guidance] <br>
**Output Format:** [Markdown with endpoint descriptions, JSON examples, and Python or shell command snippets] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Requires network access and MATON_API_KEY for live API requests.] <br>

## Skill Version(s): <br>
1.0.6 (source: server release metadata) <br>

## Ethical Considerations: <br>
Users should evaluate whether this skill is appropriate for their environment, review any generated or modified files before relying on them, and apply their organization's safety, security, and compliance requirements before deployment. <br>
