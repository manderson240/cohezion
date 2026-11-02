"""Labelled text pairs for scoring candidate text latents (written before any encoder was scored).

PARAPHRASE: same request, different wording (low lexical overlap).
HARD_NEG: same topic, different request (a false hit serves a wrong answer).
UNRELATED: different topic entirely.
"""

PARAPHRASE = [
    (
        "How do I reverse a linked list in Python?",
        "What is the way to flip the order of nodes in a singly linked list using Python?",
    ),
    (
        "Summarize this contract in three bullet points.",
        "Give me a three-bullet digest of this agreement.",
    ),
    ("Why is my pytest suite so slow?", "What is making the test run take so long?"),
    (
        "Restart the web server after the config change.",
        "Bounce the HTTP service once the settings are updated.",
    ),
    (
        "Write a function that checks whether a string is a palindrome.",
        "Implement a helper returning true when text reads the same backwards.",
    ),
    ("What is the capital of Australia?", "Which city serves as Australia's seat of government?"),
    (
        "Explain how gradient descent works.",
        "Describe the mechanism by which gradient descent minimizes a loss.",
    ),
    ("Convert this CSV file into JSON.", "Transform the comma-separated file to a JSON document."),
    (
        "The deployment failed with a timeout error.",
        "Our rollout crashed because the operation timed out.",
    ),
    (
        "Find all files modified in the last day.",
        "List every file that changed within the past 24 hours.",
    ),
    ("How can I lower my cloud bill?", "What are ways to cut down our monthly cloud spending?"),
    (
        "Draft an apology email to a customer for the delayed shipment.",
        "Compose a message saying sorry to a client about the late delivery.",
    ),
    ("Remove duplicate rows from the dataframe.", "Drop repeated records in the pandas table."),
    ("What does this regex match?", "Tell me which strings the regular expression accepts."),
    (
        "Set up a cron job that runs every night at 2am.",
        "Schedule a task to execute nightly at two in the morning.",
    ),
    ("Translate this paragraph into French.", "Render the following passage in French."),
    (
        "My model is overfitting the training data.",
        "The network memorizes the training set and fails to generalize.",
    ),
    ("How do I undo my last git commit?", "What command reverts the most recent commit in git?"),
    (
        "Review this pull request for security problems.",
        "Audit the PR looking for vulnerabilities.",
    ),
    (
        "Create a unit test for the login endpoint.",
        "Write an automated test covering the sign-in API route.",
    ),
    ("What time zone is Tokyo in?", "Which timezone does Tokyo use?"),
    ("Increase the memory limit of the container.", "Give the container a larger RAM allowance."),
    (
        "Recommend a good book about the history of Rome.",
        "Suggest a worthwhile read on ancient Roman history.",
    ),
    (
        "The API returns a 500 error when the payload is empty.",
        "Sending an empty body to the endpoint causes an internal server error.",
    ),
    (
        "Explain the difference between a process and a thread.",
        "How do processes differ from threads?",
    ),
    ("Please shorten this paragraph.", "Can you make this passage more concise?"),
    ("Rotate the API keys that were leaked.", "Replace the credentials that got exposed."),
    (
        "How many tokens fit in the context window?",
        "What is the maximum prompt length the model accepts?",
    ),
    ("Plan a three day trip to Lisbon.", "Put together an itinerary for 3 days in Lisbon."),
    ("Why does my loop never terminate?", "What keeps this while-loop from ever ending?"),
    ("Merge the feature branch into main.", "Combine the feature branch with the main branch."),
    ("Calculate the average of these numbers.", "Compute the mean of the following values."),
    ("What are the symptoms of dehydration?", "How can I tell if someone is dehydrated?"),
    (
        "Back up the database before the migration.",
        "Take a snapshot of the DB prior to running the schema change.",
    ),
    ("Generate a haiku about autumn.", "Write a three-line 5-7-5 poem on the fall season."),
    ("Check whether the service is healthy.", "Is the service up and responding normally?"),
    ("Add type hints to this function.", "Annotate the function signature with types."),
    (
        "How do I center a div in CSS?",
        "What is the CSS way to horizontally and vertically align a div?",
    ),
    (
        "Cancel my subscription at the end of the month.",
        "Please end my plan when this month finishes.",
    ),
    (
        "Profile the program to find the bottleneck.",
        "Measure where the application spends most of its time.",
    ),
]

HARD_NEG = [
    (
        "How do I reverse a linked list in Python?",
        "How do I detect a cycle in a linked list in Python?",
    ),
    (
        "Summarize this contract in three bullet points.",
        "Rewrite this contract clause to favor the buyer.",
    ),
    ("Why is my pytest suite so slow?", "Why is my pytest suite failing on CI only?"),
    ("Restart the web server after the config change.", "Shut down the web server permanently."),
    (
        "Write a function that checks whether a string is a palindrome.",
        "Write a function that counts vowels in a string.",
    ),
    ("What is the capital of Australia?", "What is the population of Australia?"),
    ("Explain how gradient descent works.", "Explain how backpropagation computes gradients."),
    ("Convert this CSV file into JSON.", "Convert this JSON file into CSV."),
    ("The deployment failed with a timeout error.", "The deployment succeeded without any errors."),
    ("Find all files modified in the last day.", "Delete all files modified in the last day."),
    ("How can I lower my cloud bill?", "How can I increase the capacity of my cloud cluster?"),
    (
        "Draft an apology email to a customer for the delayed shipment.",
        "Draft a thank-you email to a customer for the repeat order.",
    ),
    ("Remove duplicate rows from the dataframe.", "Add a new column to the dataframe."),
    (
        "Set up a cron job that runs every night at 2am.",
        "Disable the cron job that runs every night at 2am.",
    ),
    ("Translate this paragraph into French.", "Translate this paragraph into Japanese."),
    ("My model is overfitting the training data.", "My model is underfitting the training data."),
    ("How do I undo my last git commit?", "How do I sign my last git commit with GPG?"),
    (
        "Review this pull request for security problems.",
        "Review this pull request for naming style.",
    ),
    ("Increase the memory limit of the container.", "Decrease the memory limit of the container."),
    ("Merge the feature branch into main.", "Delete the feature branch after the merge."),
]

UNRELATED = [
    ("How do I reverse a linked list in Python?", "What wine pairs well with grilled salmon?"),
    (
        "Summarize this contract in three bullet points.",
        "The glacier retreated about two kilometers over the last decade.",
    ),
    ("Why is my pytest suite so slow?", "Recommend a good book about the history of Rome."),
    (
        "Restart the web server after the config change.",
        "How long should I boil an egg for a soft yolk?",
    ),
    ("What is the capital of Australia?", "My sourdough starter smells like nail polish remover."),
    ("Explain how gradient descent works.", "Plan a three day trip to Lisbon."),
    ("Convert this CSV file into JSON.", "The striker scored twice in the second half."),
    ("The deployment failed with a timeout error.", "Which houseplants tolerate low light?"),
    ("Find all files modified in the last day.", "Compose a sonnet about the sea."),
    ("How can I lower my cloud bill?", "What are the symptoms of dehydration?"),
    (
        "Draft an apology email to a customer for the delayed shipment.",
        "Explain the rules of cricket.",
    ),
    (
        "Remove duplicate rows from the dataframe.",
        "The violin concerto opens with a quiet solo passage.",
    ),
    ("Set up a cron job that runs every night at 2am.", "How do vaccines train the immune system?"),
    ("Translate this paragraph into French.", "Calculate the area of a circle with radius seven."),
    (
        "My model is overfitting the training data.",
        "Best way to remove a red wine stain from a carpet?",
    ),
    ("How do I undo my last git commit?", "Who painted the ceiling of the Sistine Chapel?"),
    (
        "Review this pull request for security problems.",
        "Describe the life cycle of a monarch butterfly.",
    ),
    ("Increase the memory limit of the container.", "I need tips for negotiating a higher salary."),
    ("Merge the feature branch into main.", "What causes the northern lights?"),
    ("Back up the database before the migration.", "Suggest a name for a golden retriever puppy."),
]
