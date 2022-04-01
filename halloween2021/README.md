# Halloween

Event module for Halloween 2021.

Warning: the code does not handle well large amounts of roles.

If you have bigger than small amount of roles, consider updating the code to make sure it fits into the limit of message content.
It will print it to stdout in case you get over the 2000 character limit and the message fails to be sent.
You have been warned.

---

**halloween color**

Color all roles orange.
This will return a mapping of all roles and their original colors.

**halloween uncolor &lt;input&gt;**

Return the original colors.
The input is the string returned by *halloween color*.
