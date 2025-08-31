// Script to fix the problematic studentId index
const { MongoClient } = require("mongodb");

async function fixStudentIndex() {
  const client = new MongoClient(
    "mongodb://admin:madrasati123@mongodb:27017/madrasati?authSource=admin"
  );

  try {
    await client.connect();
    const db = client.db("madrasati");
    const studentsCollection = db.collection("students");

    console.log("Connected to MongoDB");

    // List current indexes
    const indexes = await studentsCollection.indexes();
    console.log("Current indexes:", indexes);

    // Try to drop the problematic studentId index
    try {
      await studentsCollection.dropIndex("studentId_1");
      console.log("Successfully dropped studentId_1 index");
    } catch (err) {
      console.log("Index might not exist or already dropped:", err.message);
    }

    // List indexes after dropping
    const indexesAfter = await studentsCollection.indexes();
    console.log("Indexes after dropping:", indexesAfter);
  } catch (err) {
    console.error("Error:", err);
  } finally {
    await client.close();
  }
}

fixStudentIndex();
