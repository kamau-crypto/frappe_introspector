[ ] Add a Chat box/ interface in the base.html that expands and closes

- Persist the chat sessions using an sqlite database...
- The database should have the following fields:
  - 1.  Role
  - 2.  Message
  - 3.  Datetime
  - 4.  Thinking param
  - 5. content
  - 6. user_id
  - 7. Message_id
- Save sessions to a local DB like sql-lite... or sth..
- [ ] Add the Open API specification. Use AI to generate the open API spec for a certain doctype of group of doctypes.
      [x] Git track these changes
      [x] Get the endpoint for DocType plus customizations
      [ ] Add testability of endpoints for **Open API Specification**. (Moved to doctype specific JSON tests...)
      [x] Fix syntax highlighting for automatic syntax generation.
      [ ] Add AI for:
      [ ] Converting the type definition for different programming languages compatible type definitions.
      [ ] Doctype Details JSON compatible for POSTMAN testing. For example when working with python, a doctype detail can be used to generate some sample data, based on the fields provided as commands.
      [ ] Add credentials persistency via login and JWT for security and preventing user reusability.
      [ ] Use redis to persist session logging.
      [x] Optimize watcher. For realtime file watching during development to restart the flask server incase a watched file is changed.
- Flask by default comes with its own optimized watcher, the only thing to do is to provide with some external provision for reuse within the app.
  [x] Generate a schema that can be converted to typescript, include both optional and required params for typescript/python api compatibility.
  [x] Add Markdown Files for readability and reusability from the interface.
  [x] Work with an MCP server to aid with the autogeneration of some of the concepts.
  [x] Reverse Engineered the Safaricom Decode Hashed Number DBASE...

  [x] Deployment.
  [x] Deployment to GCP using cloud run...
  [x] Add Rate limiting to all routes that need protecting.

  [x] Add a theme toggler for the app..
  [x] Fix theming for all packages to add support for both dark mode and light mode...
  [x] Add DDOS protection. THis is done by rate-limiting strategies imposed using flask-limiter and robots.txt (Improved to limit AI and web crawler utilization)
  [x] 1. To disable crawling different pages.
  [x] 2. To enable only crawling specific routes...
  - I want to implement a feature by adding the following:
    - An AI crawlable endpoint, which will index the page by generating a page's XML sitemap. And allowing AI to crawl to provide deep linking capabilities to a page..
    - Protect the sitemap generation endpoint to just one page...

  [ ]REDIS
  [x] Redis to cache file reads. Give it a window of 5 mins before refreshing the redis cache, with some new files, to improve file reading speed.

  [ ] Add a feature to generate a shareable link for a doctype, which can be shared with other users to view the doctype details without needing to log in. This can be implemented by generating a unique token for each doctype and storing it in the database, then creating a route that allows users to access the doctype details using the token.

  [ ] Markdown copy of the doctype details to custom chatbots.

## Tips

- To export modules to the requirements.txt file, use the code below

```python

pip freeze > requirements.txt

```

## Installation

- TO install the application's modules, run the command

```python

pip install < requirements.txt

```
